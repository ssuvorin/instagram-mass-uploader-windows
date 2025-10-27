"""
Device pool for Instagram automation.

This file contains realistic Android device configurations used for generating
consistent device fingerprints and User Agent strings.
"""

from typing import List, Dict, Any

# Pool of Instagram app versions for randomization
# Each tuple contains (app_version, version_code)
INSTAGRAM_VERSION_POOL = [
    ("400.0.0.49.68", "400049068"),    # Latest
    ("395.0.0.56.165", "395056165"),  # Recent stable
    ("394.0.0.46.81", "394046081"),   # Recent stable
    ("390.0.0.43.81", "390043081"),   # Recent stable
    ("385.0.0.47.74", "385047074"),   # Recent stable
    ("383.1.0.48.78", "383148078"),   # Recent stable
    ("382.0.0.49.84", "382049084"),   # Recent stable
    ("381.2.0.53.84", "381253084"),   # Recent stable
    ("380.0.0.49.84", "380049084"),   # Recent stable
    ("379.1.0.43.80", "379143080"),   # Recent stable
    ("379.0.0.41.80", "379041080"),   # Recent stable
    ("377.1.0.48.63", "377148063"),   # Recent stable
    ("377.0.0.40.63", "377040063"),   # Recent stable
    ("376.1.0.55.68", "376155068"),   # Recent stable
    ("375.0.0.38.66", "375038066"),   # Recent stable
    ("374.0.0.43.67", "374043067"),   # Recent stable
    ("373.0.0.46.67", "373046067"),   # Recent stable
    ("372.0.0.48.60", "372048060"),   # Recent stable
    ("371.0.0.36.89", "371036089"),   # Recent stable
    ("370.0.0.42.96", "370042096"),   # Recent stable
    ("369.0.0.46.101", "369046101"),  # Recent stable
    ("368.0.0.40.96", "368040096"),   # Recent stable
    ("367.0.0.43.89", "367043089"),   # Recent stable
    ("366.0.0.34.86", "366034086"),   # Recent stable
    ("365.0.0.40.94", "365040094"),   # Recent stable
    ("364.0.0.35.86", "364035086"),   # Recent stable
    ("363.0.0.29.80", "363029080"),   # Recent stable
    ("362.0.0.33.241", "362033241"),  # Recent stable
    ("361.0.0.46.88", "361046088"),   # Recent stable
    ("360.0.0.52.192", "360052192"), # Recent stable
    ("359.2.0.64.89", "359264089"),  # Recent stable
    ("359.0.0.59.89", "359059089"),  # Recent stable
    ("358.0.0.51.97", "358051097"),  # Recent stable
    ("357.1.0.52.100", "357152100"), # Recent stable
    ("356.0.0.41.101", "356041101"), # Recent stable
    ("355.0.0.42.103", "355042103"), # Recent stable
    ("354.2.0.47.100", "354247100"), # Recent stable
    ("353.1.0.47.90", "353147090"),  # Recent stable
    ("352.0.0.38.100", "352038100"), # Recent stable
    ("351.0.0.41.106", "351041106"), # Recent stable
    ("350.1.0.46.93", "350146093"),  # Recent stable
    ("349.0.0.44.97", "349044097"),  # Recent stable
    ("348.0.0.39.101", "348039101"), # Recent stable
    ("347.0.0.44.93", "347044093"),  # Recent stable
    ("346.0.0.43.91", "346043091"),  # Recent stable
    ("345.0.0.39.96", "345039096"),  # Recent stable
    ("344.0.0.41.94", "344041094"),  # Recent stable
    ("343.0.0.37.96", "343037096"),  # Recent stable
    ("342.0.0.43.92", "342043092"),  # Recent stable
    ("341.0.0.39.88", "341039088"),  # Recent stable
    ("340.0.0.35.92", "340035092"),  # Recent stable
    ("339.0.0.40.90", "339040090"),  # Recent stable
    ("338.0.0.36.88", "338036088"),  # Recent stable
    ("337.0.0.32.86", "337032086"),  # Recent stable
    ("336.0.0.38.84", "336038084"),  # Recent stable
    ("335.0.0.34.82", "335034082"),  # Recent stable
    ("334.0.0.40.80", "334040080"),  # Recent stable
    ("333.0.0.36.78", "333036078"),  # Recent stable
    ("332.0.0.32.76", "332032076"),  # Recent stable
    ("331.0.0.38.74", "331038074"),  # Recent stable
    ("330.0.0.34.72", "330034072"),  # Recent stable
    ("329.0.0.40.70", "329040070"),  # Recent stable
    ("328.0.0.36.68", "328036068"),  # Recent stable
    ("327.0.0.32.66", "327032066"),  # Recent stable
    ("326.0.0.38.64", "326038064"),  # Recent stable
    ("325.0.0.34.62", "325034062"),  # Recent stable
    ("324.0.0.40.60", "324040060"),  # Recent stable
    ("323.0.0.36.58", "323036058"),  # Recent stable
    ("322.0.0.32.56", "322032056"),  # Recent stable
    ("321.0.0.38.54", "321038054"),  # Recent stable
    ("320.0.0.34.52", "320034052"),  # Recent stable
    ("319.0.0.40.50", "319040050"),  # Recent stable
    ("318.0.0.36.48", "318036048"),  # Recent stable
    ("317.0.0.32.46", "317032046"),  # Recent stable
    ("316.0.0.38.44", "316038044"),  # Recent stable
    ("315.0.0.34.42", "315034042"),  # Recent stable
    ("314.0.0.40.40", "314040040"),  # Recent stable
    ("313.0.0.36.38", "313036038"),  # Recent stable
    ("312.0.0.32.36", "312032036"),  # Recent stable
    ("311.0.0.38.34", "311038034"),  # Recent stable
    ("310.0.0.34.32", "310034032"),  # Recent stable
    ("309.0.0.40.30", "309040030"),  # Recent stable
    ("308.0.0.36.28", "308036028"),  # Recent stable
    ("307.0.0.32.26", "307032026"),  # Recent stable
    ("306.0.0.38.24", "306038024"),  # Recent stable
    ("305.0.0.34.22", "305034022"),  # Recent stable
    ("304.0.0.40.20", "304040020"),  # Recent stable
    ("303.0.0.36.18", "303036018"),  # Recent stable
    ("302.0.0.32.16", "302032016"),  # Recent stable
    ("301.0.0.38.14", "301038014"),  # Recent stable
    ("300.0.0.34.12", "300034012"),  # Recent stable
    ("299.0.0.40.10", "299040010"),  # Recent stable
    ("298.0.0.36.8", "298036008"),   # Recent stable
    ("297.0.0.32.6", "297032006"),   # Recent stable
    ("296.0.0.38.4", "296038004"),   # Recent stable
    ("295.0.0.34.2", "295034002"),   # Recent stable
]

# Extended device pool with many real Android devices
_DEVICE_POOL = [
    # Samsung Galaxy S Series
    {
        "manufacturer": "samsung",
        "brand": "samsung",
        "model": "SM-G973F",            # Galaxy S10
        "device": "beyond1",
        "cpu": "exynos9820",
        "dpi": "640dpi",
        "resolution": "1440x3040",
        "android_release": "10",
        "android_version": 29,
    },
    {
        "manufacturer": "samsung",
        "brand": "samsung",
        "model": "SM-G975F",            # Galaxy S10+
        "device": "beyond2",
        "cpu": "exynos9820",
        "dpi": "640dpi",
        "resolution": "1440x3040",
        "android_release": "10",
        "android_version": 29,
    },
    {
        "manufacturer": "samsung",
        "brand": "samsung",
        "model": "SM-G977B",            # Galaxy S10 5G
        "device": "beyond2lte",
        "cpu": "exynos9820",
        "dpi": "640dpi",
        "resolution": "1440x3040",
        "android_release": "10",
        "android_version": 29,
    },
    {
        "manufacturer": "samsung",
        "brand": "samsung",
        "model": "SM-G998B",            # Galaxy S21 Ultra 5G
        "device": "t2s",
        "cpu": "exynos2100",
        "dpi": "515dpi",
        "resolution": "1440x3200",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "samsung",
        "brand": "samsung",
        "model": "SM-S901B",            # Galaxy S22
        "device": "b0q",
        "cpu": "qcom",
        "dpi": "450dpi",
        "resolution": "1080x2340",
        "android_release": "12",
        "android_version": 31,
    },
    {
        "manufacturer": "samsung",
        "brand": "samsung",
        "model": "SM-S906B",            # Galaxy S22+
        "device": "b0q",
        "cpu": "qcom",
        "dpi": "450dpi",
        "resolution": "1080x2340",
        "android_release": "12",
        "android_version": 31,
    },
    {
        "manufacturer": "samsung",
        "brand": "samsung",
        "model": "SM-S908B",            # Galaxy S22 Ultra
        "device": "b0q",
        "cpu": "qcom",
        "dpi": "500dpi",
        "resolution": "1440x3088",
        "android_release": "12",
        "android_version": 31,
    },
    {
        "manufacturer": "samsung",
        "brand": "samsung",
        "model": "SM-S911B",            # Galaxy S23
        "device": "dm3q",
        "cpu": "qcom",
        "dpi": "450dpi",
        "resolution": "1080x2340",
        "android_release": "13",
        "android_version": 33,
    },
    {
        "manufacturer": "samsung",
        "brand": "samsung",
        "model": "SM-S916B",            # Galaxy S23 Ultra
        "device": "dm3q",
        "cpu": "qcom",
        "dpi": "500dpi",
        "resolution": "1440x3088",
        "android_release": "13",
        "android_version": 33,
    },

    # Samsung Galaxy Note Series
    {
        "manufacturer": "samsung",
        "brand": "samsung",
        "model": "SM-N975F",            # Galaxy Note 10+
        "device": "d2s",
        "cpu": "exynos9825",
        "dpi": "640dpi",
        "resolution": "1440x3040",
        "android_release": "10",
        "android_version": 29,
    },
    {
        "manufacturer": "samsung",
        "brand": "samsung",
        "model": "SM-N986B",            # Galaxy Note 20 Ultra 5G
        "device": "c1s",
        "cpu": "exynos990",
        "dpi": "515dpi",
        "resolution": "1440x3088",
        "android_release": "11",
        "android_version": 30,
    },

    # Samsung Galaxy A Series
    {
        "manufacturer": "samsung",
        "brand": "samsung",
        "model": "SM-A715F",            # Galaxy A71
        "device": "a71",
        "cpu": "qcom",
        "dpi": "420dpi",
        "resolution": "1080x2400",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "samsung",
        "brand": "samsung",
        "model": "SM-A525F",            # Galaxy A52
        "device": "a52",
        "cpu": "qcom",
        "dpi": "420dpi",
        "resolution": "1080x2400",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "samsung",
        "brand": "samsung",
        "model": "SM-A735F",            # Galaxy A73
        "device": "a73",
        "cpu": "qcom",
        "dpi": "420dpi",
        "resolution": "1080x2400",
        "android_release": "12",
        "android_version": 31,
    },

    # Xiaomi Redmi Series
    {
        "manufacturer": "Xiaomi",
        "brand": "Xiaomi",
        "model": "Redmi Note 8 Pro",
        "device": "begonia",
        "cpu": "mt6895",
        "dpi": "440dpi",
        "resolution": "1080x2340",
        "android_release": "10",
        "android_version": 29,
    },
    {
        "manufacturer": "Xiaomi",
        "brand": "Xiaomi",
        "model": "Redmi Note 9 Pro",
        "device": "joyeuse",
        "cpu": "mt6893",
        "dpi": "440dpi",
        "resolution": "1080x2400",
        "android_release": "10",
        "android_version": 29,
    },
    {
        "manufacturer": "Xiaomi",
        "brand": "Xiaomi",
        "model": "Redmi Note 10 Pro",
        "device": "sweet",
        "cpu": "mt6833",
        "dpi": "440dpi",
        "resolution": "1080x2400",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "Xiaomi",
        "brand": "Xiaomi",
        "model": "Redmi Note 11 Pro",
        "device": "pissarro",
        "cpu": "mt6833",
        "dpi": "440dpi",
        "resolution": "1080x2400",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "Xiaomi",
        "brand": "Xiaomi",
        "model": "Redmi Note 12 Pro",
        "device": "ruby",
        "cpu": "mt6895",
        "dpi": "440dpi",
        "resolution": "1080x2400",
        "android_release": "12",
        "android_version": 31,
    },
    {
        "manufacturer": "Xiaomi",
        "brand": "Xiaomi",
        "model": "Redmi K40 Pro",
        "device": "haydn",
        "cpu": "qcom",
        "dpi": "440dpi",
        "resolution": "1080x2400",
        "android_release": "11",
        "android_version": 30,
    },

    # Xiaomi Mi Series
    {
        "manufacturer": "Xiaomi",
        "brand": "Xiaomi",
        "model": "Mi 11",
        "device": "venus",
        "cpu": "qcom",
        "dpi": "515dpi",
        "resolution": "1440x3200",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "Xiaomi",
        "brand": "Xiaomi",
        "model": "Mi 11 Ultra",
        "device": "star",
        "cpu": "qcom",
        "dpi": "515dpi",
        "resolution": "1440x3200",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "Xiaomi",
        "brand": "Xiaomi",
        "model": "Mi 12",
        "device": "zeus",
        "cpu": "qcom",
        "dpi": "515dpi",
        "resolution": "1440x3200",
        "android_release": "12",
        "android_version": 31,
    },
    {
        "manufacturer": "Xiaomi",
        "brand": "Xiaomi",
        "model": "Mi 13",
        "device": "fuxi",
        "cpu": "qcom",
        "dpi": "515dpi",
        "resolution": "1440x3200",
        "android_release": "13",
        "android_version": 33,
    },

    # Xiaomi Poco Series
    {
        "manufacturer": "Xiaomi",
        "brand": "Xiaomi",
        "model": "POCO X3 Pro",
        "device": "vayu",
        "cpu": "qcom",
        "dpi": "440dpi",
        "resolution": "1080x2400",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "Xiaomi",
        "brand": "Xiaomi",
        "model": "POCO F3",
        "device": "alioth",
        "cpu": "qcom",
        "dpi": "440dpi",
        "resolution": "1080x2400",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "Xiaomi",
        "brand": "Xiaomi",
        "model": "POCO X4 Pro 5G",
        "device": "peux",
        "cpu": "mt6895",
        "dpi": "440dpi",
        "resolution": "1080x2400",
        "android_release": "12",
        "android_version": 31,
    },

    # Google Pixel Series
    {
        "manufacturer": "Google",
        "brand": "google",
        "model": "Pixel 5",
        "device": "redfin",
        "cpu": "qcom",
        "dpi": "440dpi",
        "resolution": "1080x2340",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "Google",
        "brand": "google",
        "model": "Pixel 5a",
        "device": "barbet",
        "cpu": "qcom",
        "dpi": "420dpi",
        "resolution": "1080x2400",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "Google",
        "brand": "google",
        "model": "Pixel 6",
        "device": "oriole",
        "cpu": "google",
        "dpi": "420dpi",
        "resolution": "1080x2400",
        "android_release": "12",
        "android_version": 31,
    },
    {
        "manufacturer": "Google",
        "brand": "google",
        "model": "Pixel 6 Pro",
        "device": "raven",
        "cpu": "google",
        "dpi": "512dpi",
        "resolution": "1440x3120",
        "android_release": "12",
        "android_version": 31,
    },
    {
        "manufacturer": "Google",
        "brand": "google",
        "model": "Pixel 7",
        "device": "panther",
        "cpu": "google",
        "dpi": "420dpi",
        "resolution": "1080x2400",
        "android_release": "13",
        "android_version": 33,
    },
    {
        "manufacturer": "Google",
        "brand": "google",
        "model": "Pixel 7 Pro",
        "device": "cheetah",
        "cpu": "google",
        "dpi": "512dpi",
        "resolution": "1440x3120",
        "android_release": "13",
        "android_version": 33,
    },
    {
        "manufacturer": "Google",
        "brand": "google",
        "model": "Pixel 8",
        "device": "shiba",
        "cpu": "google",
        "dpi": "420dpi",
        "resolution": "1080x2400",
        "android_release": "14",
        "android_version": 34,
    },
    {
        "manufacturer": "Google",
        "brand": "google",
        "model": "Pixel 8 Pro",
        "device": "husky",
        "cpu": "google",
        "dpi": "512dpi",
        "resolution": "1344x2992",
        "android_release": "14",
        "android_version": 34,
    },

    # OnePlus Series
    {
        "manufacturer": "OnePlus",
        "brand": "OnePlus",
        "model": "ONEPLUS A6013",       # OnePlus 6T
        "device": "OnePlus6T",
        "cpu": "qcom",
        "dpi": "420dpi",
        "resolution": "1080x2340",
        "android_release": "10",
        "android_version": 29,
    },
    {
        "manufacturer": "OnePlus",
        "brand": "OnePlus",
        "model": "ONEPLUS A5010",       # OnePlus 5T
        "device": "OnePlus5T",
        "cpu": "qcom",
        "dpi": "420dpi",
        "resolution": "1080x2160",
        "android_release": "9",
        "android_version": 28,
    },
    {
        "manufacturer": "OnePlus",
        "brand": "OnePlus",
        "model": "ONEPLUS A6003",       # OnePlus 6
        "device": "OnePlus6",
        "cpu": "qcom",
        "dpi": "420dpi",
        "resolution": "1080x2160",
        "android_release": "9",
        "android_version": 28,
    },
    {
        "manufacturer": "OnePlus",
        "brand": "OnePlus",
        "model": "LE2113",              # OnePlus 9 Pro
        "device": "OnePlus9Pro",
        "cpu": "qcom",
        "dpi": "525dpi",
        "resolution": "1440x3216",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "OnePlus",
        "brand": "OnePlus",
        "model": "LE2111",              # OnePlus 9
        "device": "OnePlus9",
        "cpu": "qcom",
        "dpi": "402dpi",
        "resolution": "1080x2400",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "OnePlus",
        "brand": "OnePlus",
        "model": "NE2213",              # OnePlus 10 Pro
        "device": "OnePlus10Pro",
        "cpu": "qcom",
        "dpi": "525dpi",
        "resolution": "1440x3216",
        "android_release": "12",
        "android_version": 31,
    },
    {
        "manufacturer": "OnePlus",
        "brand": "OnePlus",
        "model": "CPH2423",             # OnePlus 11
        "device": "OnePlus11",
        "cpu": "qcom",
        "dpi": "525dpi",
        "resolution": "1440x3216",
        "android_release": "13",
        "android_version": 33,
    },

    # Huawei Series
    {
        "manufacturer": "Huawei",
        "brand": "HUAWEI",
        "model": "P30",
        "device": "ELE-L29",
        "cpu": "kirin980",
        "dpi": "440dpi",
        "resolution": "1080x2340",
        "android_release": "9",
        "android_version": 28,
    },
    {
        "manufacturer": "Huawei",
        "brand": "HUAWEI",
        "model": "P40 Pro",
        "device": "ELS-NX9",
        "cpu": "kirin990",
        "dpi": "440dpi",
        "resolution": "1200x2640",
        "android_release": "10",
        "android_version": 29,
    },
    {
        "manufacturer": "Huawei",
        "brand": "HUAWEI",
        "model": "Mate 30 Pro",
        "device": "LIO-AL00",
        "cpu": "kirin990",
        "dpi": "440dpi",
        "resolution": "1176x2400",
        "android_release": "10",
        "android_version": 29,
    },
    {
        "manufacturer": "Huawei",
        "brand": "HUAWEI",
        "model": "Mate 40 Pro",
        "device": "NOH-AN00",
        "cpu": "kirin9000",
        "dpi": "440dpi",
        "resolution": "1344x2772",
        "android_release": "10",
        "android_version": 29,
    },

    # Sony Xperia Series
    {
        "manufacturer": "Sony",
        "brand": "Sony",
        "model": "XQ-CT72",             # Xperia 5 III
        "device": "XQ-CT72",
        "cpu": "qcom",
        "dpi": "449dpi",
        "resolution": "1080x2520",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "Sony",
        "brand": "Sony",
        "model": "XQ-BQ52",             # Xperia 1 III
        "device": "XQ-BQ52",
        "cpu": "qcom",
        "dpi": "643dpi",
        "resolution": "1644x3840",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "Sony",
        "brand": "Sony",
        "model": "XQ-DQ72",             # Xperia 1 IV
        "device": "XQ-DQ72",
        "cpu": "qcom",
        "dpi": "643dpi",
        "resolution": "1644x3840",
        "android_release": "12",
        "android_version": 31,
    },

    # Motorola Series
    {
        "manufacturer": "motorola",
        "brand": "motorola",
        "model": "moto g(8) plus",      # Moto G8 Plus
        "device": "sofiar",
        "cpu": "qcom",
        "dpi": "300dpi",
        "resolution": "1080x2280",
        "android_release": "10",
        "android_version": 29,
    },
    {
        "manufacturer": "motorola",
        "brand": "motorola",
        "model": "moto g(9) plus",      # Moto G9 Plus
        "device": "nairo",
        "cpu": "qcom",
        "dpi": "300dpi",
        "resolution": "1080x2400",
        "android_release": "10",
        "android_version": 29,
    },
    {
        "manufacturer": "motorola",
        "brand": "motorola",
        "model": "moto g(10) power",    # Moto G10 Power
        "device": "sofia",
        "cpu": "mt6833",
        "dpi": "300dpi",
        "resolution": "1080x2300",
        "android_release": "11",
        "android_version": 30,
    },

    # LG Series
    {
        "manufacturer": "LGE",
        "brand": "lge",
        "model": "LM-G820",             # LG G8 ThinQ
        "device": "swald",
        "cpu": "qcom",
        "dpi": "420dpi",
        "resolution": "1440x3120",
        "android_release": "9",
        "android_version": 28,
    },
    {
        "manufacturer": "LGE",
        "brand": "lge",
        "model": "LM-V600",             # LG V60 ThinQ
        "device": "flash",
        "cpu": "qcom",
        "dpi": "420dpi",
        "resolution": "1080x2460",
        "android_release": "10",
        "android_version": 29,
    },

    # ASUS Zenfone Series
    {
        "manufacturer": "asus",
        "brand": "asus",
        "model": "Zenfone 8",
        "device": "I006D",
        "cpu": "qcom",
        "dpi": "432dpi",
        "resolution": "1080x2400",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "asus",
        "brand": "asus",
        "model": "ROG Phone 5",
        "device": "I005D",
        "cpu": "qcom",
        "dpi": "432dpi",
        "resolution": "1080x2400",
        "android_release": "11",
        "android_version": 30,
    },

    # Realme Series
    {
        "manufacturer": "realme",
        "brand": "realme",
        "model": "RMX2061",             # Realme 6 Pro
        "device": "RMX2061",
        "cpu": "mt6893",
        "dpi": "420dpi",
        "resolution": "1080x2400",
        "android_release": "10",
        "android_version": 29,
    },
    {
        "manufacturer": "realme",
        "brand": "realme",
        "model": "RMX2081",             # Realme 7 Pro
        "device": "RMX2081",
        "cpu": "mt6893",
        "dpi": "420dpi",
        "resolution": "1080x2400",
        "android_release": "10",
        "android_version": 29,
    },
    {
        "manufacturer": "realme",
        "brand": "realme",
        "model": "RMX2170",             # Realme 8 Pro
        "device": "RMX2170",
        "cpu": "mt6893",
        "dpi": "420dpi",
        "resolution": "1080x2400",
        "android_release": "11",
        "android_version": 30,
    },

    # Oppo Series
    {
        "manufacturer": "OPPO",
        "brand": "OPPO",
        "model": "PEEM00",              # OPPO Reno 10x Zoom
        "device": "PEEM00",
        "cpu": "qcom",
        "dpi": "440dpi",
        "resolution": "1080x2400",
        "android_release": "9",
        "android_version": 28,
    },
    {
        "manufacturer": "OPPO",
        "brand": "OPPO",
        "model": "PEFM00",              # OPPO Find X2 Pro
        "device": "PEFM00",
        "cpu": "qcom",
        "dpi": "440dpi",
        "resolution": "1440x3168",
        "android_release": "10",
        "android_version": 29,
    },

    # Vivo Series
    {
        "manufacturer": "vivo",
        "brand": "vivo",
        "model": "V2056A",              # Vivo X60 Pro+
        "device": "V2056A",
        "cpu": "qcom",
        "dpi": "440dpi",
        "resolution": "1080x2376",
        "android_release": "11",
        "android_version": 30,
    },
    {
        "manufacturer": "vivo",
        "brand": "vivo",
        "model": "V2057A",              # Vivo S12 Pro
        "device": "V2057A",
        "cpu": "mt6895",
        "dpi": "440dpi",
        "resolution": "1080x2376",
        "android_release": "11",
        "android_version": 30,
    },

    # Nokia Series
    {
        "manufacturer": "Nokia",
        "brand": "Nokia",
        "model": "TA-1053",             # Nokia 3.1 Plus
        "device": "B2N_sprout",
        "cpu": "mt6762",
        "dpi": "320dpi",
        "resolution": "720x1440",
        "android_release": "9",
        "android_version": 28,
    },
    {
        "manufacturer": "Nokia",
        "brand": "Nokia",
        "model": "TA-1174",             # Nokia 5.3
        "device": "Polaris",
        "cpu": "mt6762",
        "dpi": "400dpi",
        "resolution": "720x1600",
        "android_release": "10",
        "android_version": 29,
    },
]
