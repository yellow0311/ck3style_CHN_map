"""Projection constants shared by the United Kingdom data generators."""


def project(lon, lat):
    return (lon + 8.8) * 51, (61.1 - lat) * 78
