class App:

    def __init__(self, app_dict):
        self.name = app_dict["name"]
        self.exec_cmd = app_dict["exec_cmd"]
        self.icon = app_dict["icon"]
        self.mime = app_dict["mime"]
        self.categories = app_dict["categories"]
        self.desktop_id = app_dict["desktop_id"]
        self.path = app_dict["path"]

    def __repr__(self):
        return f"App(name={self.name!r}, desktop_id={self.desktop_id!r})"
