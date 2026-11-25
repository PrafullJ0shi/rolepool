"""Country and region lookup for free-text job locations. Small, explicit tables; no geocoding service."""
from __future__ import annotations

COUNTRIES = {
    "US": ["united states", "united states of america", "usa", "u.s.", "u.s.a.", "us", "america"],
    "CA": ["canada"], "MX": ["mexico", "méxico"], "BR": ["brazil", "brasil"], "AR": ["argentina"],
    "CL": ["chile"], "CO": ["colombia"], "PE": ["peru"], "UY": ["uruguay"], "CR": ["costa rica"],
    "PA": ["panama"], "SV": ["el salvador"], "GT": ["guatemala"], "DO": ["dominican republic"], "PR": ["puerto rico"],
    "VE": ["venezuela"], "EC": ["ecuador"], "BO": ["bolivia"], "PY": ["paraguay"],
    "GB": ["united kingdom", "uk", "u.k.", "great britain", "england", "scotland", "wales", "northern ireland"],
    "IE": ["ireland"], "FR": ["france"], "DE": ["germany", "deutschland"], "NL": ["netherlands", "the netherlands", "holland"],
    "BE": ["belgium"], "LU": ["luxembourg"], "CH": ["switzerland", "schweiz", "suisse"], "AT": ["austria"],
    "IT": ["italy", "italia"], "ES": ["spain", "españa"], "PT": ["portugal"], "SE": ["sweden"], "NO": ["norway"],
    "DK": ["denmark"], "FI": ["finland"], "IS": ["iceland"], "PL": ["poland", "polska"], "CZ": ["czechia", "czech republic"],
    "SK": ["slovakia"], "HU": ["hungary"], "RO": ["romania"], "BG": ["bulgaria"], "GR": ["greece"], "HR": ["croatia"],
    "SI": ["slovenia"], "RS": ["serbia"], "UA": ["ukraine"], "EE": ["estonia"], "LV": ["latvia"], "LT": ["lithuania"],
    "MT": ["malta"], "CY": ["cyprus"], "GI": ["gibraltar"], "LI": ["liechtenstein"], "MC": ["monaco"], "AD": ["andorra"],
    "GE": ["georgia (country)"], "AM": ["armenia"], "TR": ["turkey", "türkiye", "turkiye"], "BA": ["bosnia"],
    "MK": ["north macedonia"], "AL": ["albania"], "ME": ["montenegro"], "MD": ["moldova"], "BY": ["belarus"],
    "AE": ["united arab emirates", "uae", "u.a.e."], "SA": ["saudi arabia", "ksa"], "QA": ["qatar"], "BH": ["bahrain"],
    "KW": ["kuwait"], "OM": ["oman"], "IL": ["israel"], "JO": ["jordan"], "LB": ["lebanon"], "EG": ["egypt"],
    "MA": ["morocco"], "TN": ["tunisia"], "NG": ["nigeria"], "KE": ["kenya"], "GH": ["ghana"], "ZA": ["south africa"],
    "RW": ["rwanda"], "UG": ["uganda"], "TZ": ["tanzania"], "ET": ["ethiopia"], "MU": ["mauritius"], "SC": ["seychelles"],
    "IN": ["india", "bharat"], "PK": ["pakistan"], "BD": ["bangladesh"], "LK": ["sri lanka"], "NP": ["nepal"],
    "SG": ["singapore"], "MY": ["malaysia"], "ID": ["indonesia"], "TH": ["thailand"], "VN": ["vietnam", "viet nam"],
    "PH": ["philippines"], "HK": ["hong kong", "hong kong sar"], "TW": ["taiwan"], "CN": ["china", "mainland china"],
    "JP": ["japan"], "KR": ["south korea", "korea", "republic of korea"], "AU": ["australia"], "NZ": ["new zealand"],
    "KH": ["cambodia"], "MN": ["mongolia"], "KZ": ["kazakhstan"], "UZ": ["uzbekistan"], "BS": ["bahamas"],
    "BM": ["bermuda"], "KY": ["cayman islands"], "VG": ["british virgin islands", "bvi"], "SV2": [],
}

CITIES = {
    # North America
    "new york": "US", "nyc": "US", "brooklyn": "US", "san francisco": "US", "sf": "US", "bay area": "US",
    "los angeles": "US", "seattle": "US", "austin": "US", "chicago": "US", "boston": "US", "miami": "US",
    "denver": "US", "atlanta": "US", "dallas": "US", "houston": "US", "washington": "US", "d.c.": "US",
    "palo alto": "US", "menlo park": "US", "mountain view": "US", "san jose": "US", "san diego": "US",
    "portland": "US", "philadelphia": "US", "salt lake city": "US", "phoenix": "US", "nashville": "US",
    "charlotte": "US", "jersey city": "US", "stamford": "US", "pittsburgh": "US", "minneapolis": "US",
    "detroit": "US", "raleigh": "US", "boulder": "US", "sioux falls": "US", "omaha": "US", "las vegas": "US",
    "toronto": "CA", "vancouver": "CA", "montreal": "CA", "montréal": "CA", "calgary": "CA", "ottawa": "CA", "waterloo": "CA",
    "mexico city": "MX", "guadalajara": "MX", "são paulo": "BR", "sao paulo": "BR", "rio de janeiro": "BR",
    "buenos aires": "AR", "bogotá": "CO", "bogota": "CO", "medellín": "CO", "medellin": "CO", "santiago": "CL",
    "lima": "PE", "montevideo": "UY", "san salvador": "SV",
    # Europe
    "london": "GB", "manchester": "GB", "edinburgh": "GB", "cambridge, uk": "GB", "bristol": "GB",
    "dublin": "IE", "paris": "FR", "berlin": "DE", "munich": "DE", "münchen": "DE", "frankfurt": "DE", "hamburg": "DE",
    "amsterdam": "NL", "rotterdam": "NL", "brussels": "BE", "zurich": "CH", "zürich": "CH", "zug": "CH",
    "geneva": "CH", "genève": "CH", "lugano": "CH", "basel": "CH", "vienna": "AT", "wien": "AT", "milan": "IT",
    "milano": "IT", "rome": "IT", "madrid": "ES", "barcelona": "ES", "valencia": "ES", "lisbon": "PT", "lisboa": "PT",
    "porto": "PT", "stockholm": "SE", "oslo": "NO", "copenhagen": "DK", "helsinki": "FI", "warsaw": "PL",
    "kraków": "PL", "krakow": "PL", "wroclaw": "PL", "wrocław": "PL", "prague": "CZ", "praha": "CZ", "budapest": "HU",
    "bucharest": "RO", "bucurești": "RO", "sofia": "BG", "athens": "GR", "zagreb": "HR", "ljubljana": "SI",
    "belgrade": "RS", "kyiv": "UA", "kiev": "UA", "tallinn": "EE", "riga": "LV", "vilnius": "LT", "valletta": "MT",
    "limassol": "CY", "nicosia": "CY", "luxembourg city": "LU", "vaduz": "LI", "istanbul": "TR", "tbilisi": "GE",
    "yerevan": "AM",
    # MEA
    "dubai": "AE", "abu dhabi": "AE", "riyadh": "SA", "doha": "QA", "manama": "BH", "tel aviv": "IL",
    "jerusalem": "IL", "haifa": "IL", "cairo": "EG", "lagos": "NG", "nairobi": "KE", "accra": "GH",
    "cape town": "ZA", "johannesburg": "ZA", "kigali": "RW",
    # APAC
    "singapore": "SG", "hong kong": "HK", "tokyo": "JP", "osaka": "JP", "seoul": "KR", "taipei": "TW",
    "shanghai": "CN", "beijing": "CN", "shenzhen": "CN", "bangalore": "IN", "bengaluru": "IN", "mumbai": "IN",
    "delhi": "IN", "new delhi": "IN", "gurgaon": "IN", "gurugram": "IN", "noida": "IN", "hyderabad": "IN",
    "pune": "IN", "chennai": "IN", "kolkata": "IN", "ahmedabad": "IN", "jaipur": "IN", "kuala lumpur": "MY",
    "jakarta": "ID", "bali": "ID", "bangkok": "TH", "ho chi minh": "VN", "hanoi": "VN", "manila": "PH",
    "sydney": "AU", "melbourne": "AU", "brisbane": "AU", "perth": "AU", "auckland": "NZ", "wellington": "NZ",
    "karachi": "PK", "lahore": "PK", "islamabad": "PK", "dhaka": "BD", "colombo": "LK", "almaty": "KZ",
}

US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware", "florida",
    "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi", "missouri", "montana", "nebraska",
    "nevada", "new hampshire", "new jersey", "new mexico", "north carolina", "north dakota", "ohio", "oklahoma",
    "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota", "tennessee", "texas", "utah",
    "vermont", "virginia", "west virginia", "wisconsin", "wyoming",
}
US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY",
    "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
}

REGION_OF = {}
for _c in ["US", "CA"]:
    REGION_OF[_c] = "North America"
for _c in ["MX", "BR", "AR", "CL", "CO", "PE", "UY", "CR", "PA", "SV", "GT", "DO", "PR", "VE", "EC", "BO", "PY", "BS", "BM", "KY", "VG"]:
    REGION_OF[_c] = "Latin America"
for _c in ["GB", "IE", "FR", "DE", "NL", "BE", "LU", "CH", "AT", "IT", "ES", "PT", "SE", "NO", "DK", "FI", "IS", "PL",
           "CZ", "SK", "HU", "RO", "BG", "GR", "HR", "SI", "RS", "UA", "EE", "LV", "LT", "MT", "CY", "GI", "LI", "MC",
           "AD", "GE", "AM", "TR", "BA", "MK", "AL", "ME", "MD", "BY"]:
    REGION_OF[_c] = "Europe"
for _c in ["AE", "SA", "QA", "BH", "KW", "OM", "IL", "JO", "LB", "EG", "MA", "TN", "NG", "KE", "GH", "ZA", "RW", "UG", "TZ", "ET", "MU", "SC"]:
    REGION_OF[_c] = "Middle East & Africa"
for _c in ["IN", "PK", "BD", "LK", "NP", "SG", "MY", "ID", "TH", "VN", "PH", "HK", "TW", "CN", "JP", "KR", "AU", "NZ", "KH", "MN", "KZ", "UZ"]:
    REGION_OF[_c] = "Asia-Pacific"

REGION_WORDS = {
    "emea": ["Europe", "Middle East & Africa"], "europe": ["Europe"], "european": ["Europe"], "eu": ["Europe"],
    "apac": ["Asia-Pacific"], "asia": ["Asia-Pacific"], "asia pacific": ["Asia-Pacific"], "asia-pacific": ["Asia-Pacific"],
    "latam": ["Latin America"], "latin america": ["Latin America"], "south america": ["Latin America"],
    "americas": ["North America", "Latin America"], "north america": ["North America"], "na": ["North America"],
    "middle east": ["Middle East & Africa"], "mena": ["Middle East & Africa"], "africa": ["Middle East & Africa"],
    "gcc": ["Middle East & Africa"], "cet": ["Europe"], "est": ["North America"], "pst": ["North America"],
}

REGIONS = ["North America", "Latin America", "Europe", "Middle East & Africa", "Asia-Pacific", "Global"]

_ALIAS = {}
for code, names in COUNTRIES.items():
    for n in names:
        _ALIAS[n] = code
_ALIAS.pop("georgia (country)", None)
