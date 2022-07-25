class VoteManager:
    def __init__(self, google_spreadsheet_manager):
        self.google_spreadsheet_manager = google_spreadsheet_manager

    def _add_value(self, user_id, amount, reason):
        user_columns = self.google_spreadsheet_manager.get_user_columns(user_id)
        row_to_add_data_into = self.google_spreadsheet_manager.get_first_non_empty_row(user_columns[1])
        self.google_spreadsheet_manager.add_row_data(row_to_add_data_into, column, [reason, amount])

    def up(self, user_id, reason):
        self._add_value(user_id, 1, reason)

    def down(self, user_id, reason):
        self._add_value(user_id, -1, reason)

    def get_total_value(self, user_id):
        user_columns = self.google_spreadsheet_manager.get_user_columns(user_id)
        non_empty_rows = self.google_spreadsheet_manager.get_column_data(user_columns[1])
        non_empty_cells = [int(row[0]) for row in non_empty_rows]
        return sum(non_empty_cells)

    def get_total_values(self):
        total = {}
        for user_id in self.google_spreadsheet_manager.get_mapped_users():
            total[user_id] = self.get_total_value(user_id)
        return total
    