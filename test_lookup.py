import requests

def get_ddc_from_open_library(query):
    """Search Open Library for DDC"""
    try:
        url = "https://openlibrary.org/search.json"
        params = {"q": query, "fields": "ddc,title,author_name", "limit": 1}
        print(f"Querying: {url} with params {params}")
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get("numFound", 0) > 0:
                doc = data["docs"][0]
                ddc_list = doc.get("ddc", [])
                title = doc.get("title", "Unknown")
                print(f"Found: {title}, DDC: {ddc_list}")
                if ddc_list:
                    return ddc_list[0], title
            else:
                print("No results found.")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"  Error querying API: {e}")

    return None, None

get_ddc_from_open_library("Lingua Latina Pars II Roma Aeterna")
