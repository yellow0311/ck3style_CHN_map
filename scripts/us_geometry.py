"""Project longitude and latitude in the atlas's US views."""


def project(lon, lat):
    return ((lon - 360 if lon > 0 else lon) + 125) * 14, (50 - lat) * 18
