import sqlite3

# Load SpatiaLite extension
class spatialiteConnection(sqlite3.Connection):
    def loadSpatialite(self) -> bool:
        # Enable extension
        self.enable_load_extension(True)  
        err = []
        # Load extension
        spatialiteExtensions = [
            "mod_spatialite",  # Windows or some Linux, install the whole mod_spatialite-5.1.0-win-amd64 in C:\Windows\System on Windows
            "libspatialite",   # Other system
            "spatialite"       # Backup name
        ]
        loaded = False
        for extName in spatialiteExtensions:
            try:
                self.load_extension(extName)
                loaded = True
                break
            except sqlite3.OperationalError as e:
                err.append(e)
                continue

        if not loaded:
            errstr = "Failed to load SpatiaLite extension: \n"
            for e in err:
                errstr += (str(e) + "\n")
            raise RuntimeError(errstr + "Ensure it is installed.")
        
        return loaded