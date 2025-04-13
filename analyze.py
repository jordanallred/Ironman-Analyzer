import datetime

import polars as pl
from pathlib import Path
import json

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import (
    DataTable,
    Header,
    Footer,
    Static,
    Select,
    ListView,
    ListItem,
    Label,
)
from rich.text import Text


def load_race_data(filepath: str, relevant_columns: list[str]) -> pl.DataFrame:
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON from {filepath}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error reading {filepath}: {e}") from e

    if "resultsJson" not in data or "value" not in data["resultsJson"]:
        raise ValueError("JSON structure missing 'resultsJson' or 'value' key.")

    df = pl.DataFrame(data["resultsJson"]["value"])
    existing_columns = [col for col in relevant_columns if col in df.columns]
    missing_cols = set(relevant_columns) - set(existing_columns)
    if missing_cols:
        pass

    selected_df = df.select(existing_columns)

    unformatted_columns = [
        "wtc_swimtime",
        "wtc_biketime",
        "wtc_runtime",
    ]

    for column in unformatted_columns:
        if column in selected_df.columns:
            selected_df = selected_df.with_columns(
                [
                    selected_df[column]
                    .map_elements(lambda x: datetime.timedelta(seconds=int(x)))
                    .alias(f"{column}_formatted")
                ]
            )
            selected_df = selected_df.drop(column)

    mapping = {
        "athlete": "name",
        "_wtc_agegroupid_value_formatted": "age_group",
        "wtc_finishtimeformatted": "overall_time",
        "wtc_finishrankgroup": "age_group_rank",
        "wtc_swimtime_formatted": "swim_time",
        "wtc_biketime_formatted": "bike_time",
        "wtc_runtime_formatted": "run_time",
        "wtc_finisher": "finisher",
    }

    selected_df = selected_df.rename(mapping)

    return selected_df


def get_qualifying_slots(filepath):
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON from {filepath}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error reading {filepath}: {e}") from e

    if "resultsJson" not in data or "value" not in data["resultsJson"]:
        raise ValueError("JSON structure missing 'resultsJson' or 'value' key.")

    results = data["resultsJson"]["value"]
    ironman_name = " ".join(results[0]["_wtc_eventid_value_formatted"].split()[1:])

    try:
        with open("qualifying_slots.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON from {filepath}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error reading {filepath}: {e}") from e

    ironman_slots = data["slots"][ironman_name]
    mens_slots = ironman_slots["men_slots"]
    women_slots = ironman_slots["women_slots"]

    return mens_slots, women_slots


def calculate_slot_allocation(
    data_frame: pl.DataFrame, mens_slots: int, womens_slots: int
) -> dict:
    """
    Calculate slot allocation based on the provided rules using age groups from selector.json as ground truth.

    Returns a dictionary with age groups as keys and the number of slots as values.
    """

    df = data_frame.clone()

    try:
        with open("selector.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as e:
        raise ValueError(f"Error decoding JSON from selector.json: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error reading selector.json: {e}") from e

    valid_age_groups = data["agegroups"]

    df = df.with_columns(
        pl.col("age_group").str.slice(0, 1).alias("gender"),
        pl.lit(1).alias("starters"),
    )

    df = df.filter(pl.col("age_group").is_in(valid_age_groups))

    finishers_df = df.filter(pl.col("finisher"))

    starters_by_age_group = df.group_by("age_group", "gender").agg(
        pl.sum("starters").alias("starters_count")
    )

    finishers_by_age_group = finishers_df.group_by("age_group", "gender").agg(
        pl.len().alias("finishers_count")
    )

    slot_df = starters_by_age_group.join(
        finishers_by_age_group, on=["age_group", "gender"], how="left"
    ).with_columns(pl.col("finishers_count").fill_null(0))

    slot_allocation = {ag: 0 for ag in valid_age_groups}

    male_slots_total = mens_slots
    female_slots_total = womens_slots

    for row in slot_df.iter_rows(named=True):
        age_group = row["age_group"]
        gender = row["gender"]

        if row["starters_count"] == 0:
            continue

        slot_allocation[age_group] = 1

        if gender == "M":
            male_slots_total -= 1
        else:
            female_slots_total -= 1

    print(slot_allocation)

    male_groups = slot_df.filter(
        (pl.col("gender") == "M") & (pl.col("starters_count") > 0)
    )
    female_groups = slot_df.filter(
        (pl.col("gender") == "F") & (pl.col("starters_count") > 0)
    )

    if male_slots_total > 0 and not male_groups.is_empty():
        total_male_starters = male_groups["starters_count"].sum()

        if total_male_starters > 0:
            male_props = male_groups.with_columns(
                (
                    pl.col("starters_count") / total_male_starters * male_slots_total
                ).alias("prop_slots")
            )

            for row in male_props.iter_rows(named=True):
                age_group = row["age_group"]
                additional_slots = int(row["prop_slots"])
                slot_allocation[age_group] += additional_slots
                male_slots_total -= additional_slots

            if male_slots_total > 0:
                decimal_parts = []
                for row in male_props.iter_rows(named=True):
                    decimal_part = row["prop_slots"] - int(row["prop_slots"])
                    decimal_parts.append((row["age_group"], decimal_part))

                decimal_parts.sort(key=lambda x: x[1], reverse=True)

                for i in range(int(male_slots_total)):
                    if i < len(decimal_parts):
                        slot_allocation[decimal_parts[i][0]] += 1

    if female_slots_total > 0 and not female_groups.is_empty():
        total_female_starters = female_groups["starters_count"].sum()

        if total_female_starters > 0:
            female_props = female_groups.with_columns(
                (
                    pl.col("starters_count")
                    / total_female_starters
                    * female_slots_total
                ).alias("prop_slots")
            )

            for row in female_props.iter_rows(named=True):
                age_group = row["age_group"]
                additional_slots = int(row["prop_slots"])
                slot_allocation[age_group] += additional_slots
                female_slots_total -= additional_slots

            if female_slots_total > 0:
                decimal_parts = []
                for row in female_props.iter_rows(named=True):
                    decimal_part = row["prop_slots"] - int(row["prop_slots"])
                    decimal_parts.append((row["age_group"], decimal_part))

                decimal_parts.sort(key=lambda x: x[1], reverse=True)

                for i in range(int(female_slots_total)):
                    if i < len(decimal_parts):
                        slot_allocation[decimal_parts[i][0]] += 1

    for row in slot_df.iter_rows(named=True):
        age_group = row["age_group"]
        gender = row["gender"]

        if (
            row["starters_count"] > 0
            and row["finishers_count"] == 0
            and age_group in slot_allocation
            and slot_allocation[age_group] > 0
        ):
            reallocate_slots = slot_allocation[age_group]
            slot_allocation[age_group] = 0

            if gender == "M":
                target_groups = male_groups.filter(pl.col("finishers_count") > 0)
            else:
                target_groups = female_groups.filter(pl.col("finishers_count") > 0)

            if not target_groups.is_empty():
                ratios = []
                for trow in target_groups.iter_rows(named=True):
                    tgroup = trow["age_group"]
                    ratio = trow["starters_count"] / max(
                        1, slot_allocation.get(tgroup, 1)
                    )
                    ratios.append((tgroup, ratio))

                ratios.sort(key=lambda x: x[1], reverse=True)

                for i in range(reallocate_slots):
                    if i < len(ratios):
                        slot_allocation[ratios[i][0]] += 1

    for age_group in valid_age_groups:
        if age_group not in slot_allocation:
            slot_allocation[age_group] = 0

    return slot_allocation


def determine_qualifiers(df: pl.DataFrame, slot_allocation: dict) -> list:
    """
    Determine which participants qualify based on their age group and rank.

    Returns a list of row indices for qualifying athletes.
    """
    qualifiers = []

    df_with_index = df.with_row_index("row_idx")

    for age_group, slots in slot_allocation.items():
        if slots <= 0:
            continue

        group_df = df_with_index.filter(
            (pl.col("age_group") == age_group) & (pl.col("finisher"))
        )

        if group_df.is_empty():
            continue

        group_df = group_df.sort("age_group_rank")

        top_finishers = group_df.head(slots)

        qualifiers.extend(top_finishers["row_idx"].to_list())

    return qualifiers


class LandingPage(Screen):
    """Screen to display and select JSON files from the results directory."""

    CSS = """
    ListView {
        height: 1fr;
        overflow: auto;
        margin: 1;
    }
    Label#instructions {
        margin: 1;
        content-align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label("Select a JSON file to analyze", id="instructions")
        self.file_list = ListView(id="file-list")
        yield self.file_list
        yield Footer()

    def on_mount(self) -> None:
        """Populate the list with JSON files from the results directory."""
        results_dir = Path("results")
        json_files = sorted([f.name for f in results_dir.glob("*.json") if f.is_file()])

        if not json_files:
            self.notify("No JSON files found in 'results' directory.", severity="error")
            self.app.exit()
            return

        for file_name in json_files:
            self.file_list.append(ListItem(Label(file_name), name=file_name))

        self.file_list.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle selection of a JSON file."""
        selected_file = event.item.name
        if selected_file:
            json_path = str(Path("results") / selected_file)
            self.app.push_screen(IronmanResultsScreen(json_path=json_path))


class IronmanResultsScreen(Screen):
    """Screen to display and analyze race results."""

    CSS = """
    Screen {
        overflow: auto;
    }
    #table-container {
        overflow: auto;
    }
    #filter-select {
        width: 100%;
        height: auto;
        margin-top: 1;
        display: block;
    }
    #filename {
        padding: 0 1;
        height: 1;
    }

    /* Apply highlighting to cells with the qualifier-highlight class */
    .qualifier-highlight {
        background: #6fcb9f; /* Green highlight color for qualifiers */
        color: #000000 !important;
    }
    """

    BINDINGS = [
        ("^q", "quit", "Quit"),
        ("s", "sort_column", "Sort"),
        ("f", "filter_column", "Filter"),
        ("r", "reset_view", "Reset"),
        ("h", "highlight_qualifiers", "Highlight Qualifiers"),
        ("escape", "escape", "Back"),
    ]

    def __init__(self, json_path: str, **kwargs):
        super().__init__(**kwargs)

        self.json_path = json_path
        self.df: pl.DataFrame | None = None
        self.filtered_df: pl.DataFrame | None = None
        self.relevant_columns = [
            "athlete",
            "_wtc_agegroupid_value_formatted",
            "wtc_finishtimeformatted",
            "wtc_finishrankgroup",
            "wtc_swimtime",
            "wtc_biketime",
            "wtc_runtime",
            "wtc_finisher",
        ]
        self.sort_column: str | None = None
        self.sort_descending: bool = False
        self.filter_column_name: str | None = None
        self.active_filters: dict[str, any] = {}
        self._setting_select_value: bool = False
        self.qualifier_rows: list[int] = []
        self.mens_slots: int = 0
        self.womens_slots: int = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Loading: {Path(self.json_path).name}", id="filename")
        self.table = DataTable(zebra_stripes=True, id="results-table")
        yield self.table
        self.filter_select = Select(options=[], id="filter-select")
        self.filter_select.display = False
        yield self.filter_select
        yield Footer()

    def on_mount(self) -> None:
        try:
            self.df = load_race_data(self.json_path, self.relevant_columns)

            try:
                self.mens_slots, self.womens_slots = get_qualifying_slots(
                    self.json_path
                )

                self.query_one("#filename", Static).update(
                    f"Loaded: {Path(self.json_path).name} - Men's slots: {self.mens_slots}, Women's slots: {self.womens_slots}"
                )
            except Exception as e:
                self.notify(f"Could not load qualifying slots: {e}", severity="warning")
                self.mens_slots, self.womens_slots = 0, 0
                self.query_one("#filename", Static).update(
                    f"Loaded: {Path(self.json_path).name} - Qualifying slots data not available"
                )
        except FileNotFoundError:
            self.notify(
                f"Error: JSON file not found at '{self.json_path}'",
                severity="error",
                timeout=10,
            )
            self.app.pop_screen()
            return
        except (ValueError, RuntimeError, Exception) as e:
            self.notify(f"Error loading data: {e}", severity="error", timeout=10)
            self.app.pop_screen()
            return

        self.apply_filters_and_populate()
        self.table.focus()

    def apply_filters_and_populate(self):
        if self.df is None:
            self.table.clear(columns=True)
            return

        temp_df = self.df

        if self.active_filters:
            try:
                expressions = []
                for column, value in self.active_filters.items():
                    if column not in temp_df.columns:
                        self.notify(
                            f"Filter column '{column}' not found, skipping.",
                            severity="warning",
                        )
                        continue
                    if value is None:
                        expressions.append(pl.col(column).is_null())
                    else:
                        expressions.append(pl.col(column) == value)

                if expressions:
                    combined_expression = expressions[0]
                    for expr in expressions[1:]:
                        combined_expression = combined_expression & expr
                    temp_df = temp_df.filter(combined_expression)

            except pl.PolarsError as e:
                self.notify(f"Error applying Polars filter: {e}", severity="error")
            except Exception as e:
                self.notify(f"Unexpected error during filtering: {e}", severity="error")

        if self.sort_column and self.sort_column in temp_df.columns:
            try:
                temp_df = temp_df.sort(
                    self.sort_column, descending=self.sort_descending, nulls_last=True
                )
            except pl.PolarsError as e:
                self.notify(
                    f"Could not apply sort on '{self.sort_column}': {e}",
                    severity="warning",
                )
            except Exception as e:
                self.notify(f"Unexpected error during sorting: {e}", severity="error")

        self.filtered_df = temp_df
        self.populate_table()

    def populate_table(self):
        if self.filtered_df is None:
            self.table.clear(columns=True)
            return

        self.table.clear(columns=True)
        if self.filtered_df.is_empty():
            if self.df is not None and self.df.columns:
                self.table.add_columns(*self.df.columns)
            return

        self.table.add_columns(*self.filtered_df.columns)

        try:
            original_df_with_index = None
            qualifier_athletes = []

            if self.qualifier_rows:
                original_df_with_index = self.df.with_row_index("row_idx")
                qualifier_athletes = (
                    original_df_with_index.filter(
                        pl.col("row_idx").is_in(self.qualifier_rows)
                    )
                    .select("name")
                    .to_series()
                    .to_list()
                )

            for row_dict in self.filtered_df.iter_rows(named=True):
                row_values = []

                is_qualifier = row_dict["name"] in qualifier_athletes

                for col_name, value in row_dict.items():
                    cell_text = str(value) if value is not None else ""

                    if is_qualifier:
                        text = Text(cell_text, style="bold #6fcb9f")
                    else:
                        text = Text(cell_text)

                    row_values.append(text)

                self.table.add_row(*row_values, height=1)

        except Exception as e:
            self.notify(f"Error populating table rows: {e}", severity="error")

        self.table.cursor_type = "cell"
        self.table.focus()

    def action_sort_column(self) -> None:
        if self.df is None:
            self.notify("Data not loaded yet.", severity="warning")
            return

        current_columns = (
            self.filtered_df.columns
            if self.filtered_df is not None and not self.filtered_df.is_empty()
            else self.df.columns
        )
        if not current_columns:
            self.notify("No columns available for sorting.", severity="warning")
            return

        col_index = self.table.cursor_column
        if col_index is None or col_index >= len(current_columns):
            self.notify("Invalid column selected for sorting.", severity="warning")
            return

        column = current_columns[col_index]

        if self.sort_column == column:
            self.sort_descending = not self.sort_descending
        else:
            self.sort_column = column
            self.sort_descending = False

        self.notify(
            f"Sorting by '{column}' {'descending' if self.sort_descending else 'ascending'}."
        )
        self.apply_filters_and_populate()

    def action_reset_view(self) -> None:
        """Reset all filters, sorting, and highlighting."""
        self.active_filters.clear()
        self.sort_column = None
        self.sort_descending = False
        self.filter_column_name = None
        self.qualifier_rows = []

        if self.filter_select:
            self.filter_select.display = False

        self.apply_filters_and_populate()

        self.notify("View reset. All filters, sorting, and highlights removed.")

    def action_filter_column(self) -> None:
        if self.df is None:
            self.notify("Data not loaded yet.", severity="warning")
            return

        col_index = self.table.cursor_column

        current_columns = (
            self.filtered_df.columns
            if self.filtered_df is not None and not self.filtered_df.is_empty()
            else self.df.columns
        )
        if not current_columns:
            self.notify("No columns available for filtering.", severity="warning")
            return

        if col_index is None or col_index >= len(current_columns):
            self.notify("Select a column first.", severity="warning")
            return

        column = current_columns[col_index]

        try:
            dtype = self.df.schema[column]
            if dtype != pl.Utf8 and dtype != pl.Boolean:
                self.notify(
                    f"Filtering only for text/boolean columns ('{column}' is {dtype}).",
                    severity="warning",
                )
                return
        except KeyError:
            self.notify(
                f"Column '{column}' not found in original data schema.",
                severity="error",
            )
            return

        try:
            unique_values = (
                self.df.select(column).unique().sort(by=column)[column].to_list()
            )
            if not unique_values and None not in unique_values:
                self.notify(
                    f"No unique values found to filter in column '{column}'.",
                    severity="information",
                )
                return
        except Exception as e:
            self.notify(
                f"Error getting unique values for '{column}': {e}", severity="error"
            )
            return

        self.filter_column_name = column

        options = []
        has_none = False
        processed_values = set()
        for v in unique_values:
            if v is None:
                if not has_none:
                    options.append(("None", None))
                    has_none = True
            elif str(v) not in processed_values:
                options.append((str(v), v))
                processed_values.add(str(v))

        options.sort(key=lambda x: str(x[0]) if x[1] is not None else "!")
        options.insert(0, ("-- Clear Filter --", "--clear--"))

        self._setting_select_value = True
        try:
            self.filter_select.set_options(options)
            self.filter_select.value = Select.BLANK
            self.filter_select.display = True
            self.filter_select.focus()
        except Exception as e:
            self.notify(f"Error setting up filter select: {e}", severity="error")
            self._setting_select_value = False
            self.filter_column_name = None
            self.filter_select.display = False
            self.table.focus()
        else:
            self._setting_select_value = False

    def on_select_changed(self, event: Select.Changed) -> None:
        if self._setting_select_value:
            return

        if event.control != self.filter_select or not self.filter_column_name:
            return

        column = self.filter_column_name
        value = event.value

        self.filter_select.display = False
        self.filter_column_name = None

        filter_changed = False

        if value is Select.BLANK:
            self.notify("Filter selection cancelled.")
        elif value == "--clear--":
            if column in self.active_filters:
                del self.active_filters[column]
                self.notify(f"Filter cleared for column '{column}'.")
                filter_changed = True
            else:
                self.notify(f"No active filter to clear for '{column}'.")
        else:
            filter_value = value
            current_filter = self.active_filters.get(column)
            if current_filter != filter_value:
                self.active_filters[column] = filter_value
                display_value = "None" if filter_value is None else str(filter_value)
                self.notify(f"Filter applied: '{column}' = '{display_value}'.")
                filter_changed = True
            else:
                display_value = "None" if filter_value is None else str(filter_value)
                self.notify(f"Filter unchanged: '{column}' remains '{display_value}'.")

        if filter_changed:
            try:
                self.apply_filters_and_populate()
            except Exception as e:
                self.notify(f"Error applying filters: {e}", severity="error")

        self.table.focus()

    def action_highlight_qualifiers(self) -> None:
        """Highlight participants who would qualify for world championships."""

        if self.df is None:
            self.notify("Data not loaded yet.", severity="warning")
            return

        if self.mens_slots == 0 and self.womens_slots == 0:
            self.notify("No qualifying slot information available.", severity="warning")
            return

        if self.qualifier_rows:
            self.qualifier_rows = []
            self.populate_table()
            return

        try:
            slot_allocation = calculate_slot_allocation(
                self.df, self.mens_slots, self.womens_slots
            )

            mens_slots = sum(
                [slots for age, slots in slot_allocation.items() if age.startswith("M")]
            )
            womens_slots = sum(
                [slots for age, slots in slot_allocation.items() if age.startswith("F")]
            )
            self.notify(
                f"Successfully allocated {mens_slots} men's slots and {womens_slots} women's slots",
                severity="information",
            )

            self.qualifier_rows = determine_qualifiers(self.df, slot_allocation)

            if not self.qualifier_rows:
                self.notify("No qualifying athletes found.", severity="warning")
                return

            self.populate_table()

            self.notify(
                f"Highlighted {len(self.qualifier_rows)} qualifying athletes with green text."
            )

        except Exception as e:
            self.notify(f"Error highlighting qualifiers: {str(e)}", severity="error")
            import traceback

            self.notify(traceback.format_exc(), severity="error")


class IronmanResultsApp(App):
    """Main application managing multiple screens."""

    def on_mount(self) -> None:
        self.push_screen(LandingPage())


if __name__ == "__main__":
    IronmanResultsApp().run()
