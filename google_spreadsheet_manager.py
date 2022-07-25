import gspread

class GoogleSpreadsheetManager:
    def __init__(
        self, 
        account_dict, 
        spreadsheet_id,
        spreadsheet_user_columns,
        spreadsheet_first_data_row
    ):
        self.client = gspread.service_account_from_dict(account_dict)
        self.worksheet = self.client.open_by_key(spreadsheet_id).get_worksheet(0)
        self.spreadsheet_user_columns = spreadsheet_user_columns
        self.spreadsheet_first_data_row = spreadsheet_first_data_row

    def get_user_columns(self, user_id):
        columns = self.spreadsheet_user_columns[user_id]
        if columns is None:
            raise Exception("Invalid user provided")
        return columns

    def get_mapped_users(self):
        return self.spreadsheet_user_columns.keys()

    def get_column_data(self, column_name):
        data_range = f"{column_name}{self.spreadsheet_first_data_row}:{column_name}"
        return self.worksheet.get(data_range)

    def get_first_non_empty_row(self, column_name):
        return self.spreadsheet_first_data_row + len(self.get_column_data(column_name))
    
    def add_row_data(self, row, column_range, data):
        [column_from, column_to] = column_range
        data_range = f"{column[0]}{row}:{column[1]}{row}"
        self.worksheet.update(data_range, [data])
