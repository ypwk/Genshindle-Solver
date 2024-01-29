from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

import pandas as pd


def load_data():
    try:
        df = pd.read_csv("archive/genshin_updated.csv", encoding="ISO-8859-1")
        return df
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def read_guess_headers(browser):
    headers = []
    guess_header_table = browser.find_element(By.CLASS_NAME, "guess-header")
    header_cells = guess_header_table.find_elements(By.TAG_NAME, "th")
    for header_cell in header_cells:
        headers.append(header_cell.text)
    return headers


def read_guess_table(browser):
    table_data = []
    headers = read_guess_headers(browser)
    guess_table_section = browser.find_element(By.CLASS_NAME, "guess-table")
    rows = guess_table_section.find_elements(By.TAG_NAME, "tr")

    correct_color = "rgb(29, 145, 40)"

    for row in rows:
        row_data = {}
        cells = row.find_elements(By.TAG_NAME, "td")

        for i, cell in enumerate(cells):
            style_attribute = cell.get_attribute("style")
            is_correct = correct_color in style_attribute
            if "vrs" in cell.get_attribute("class"):
                version_info = cell.find_element(By.CSS_SELECTOR, "div.back.version")
                version_text = version_info.text
                row_data[headers[i]] = [version_text, is_correct]
            else:
                if cell.text.strip() != "":
                    row_data[headers[i]] = [cell.text.strip(), is_correct]
                else:
                    images = cell.find_elements(By.TAG_NAME, "img")
                    alt_text = images[0].get_attribute("alt")
                    row_data[headers[i]] = [alt_text, is_correct]

        table_data.append(row_data)

    return table_data


def check_win(browser):
    try:
        win_state_div = browser.find_element(By.ID, "guess-right-text")
        if win_state_div:
            if "won" not in win_state_div.text:
                print(win_state_div.text)
                print(read_guess_table(browser))
                print("Proceeding to next round.")
            next_round_button = browser.find_element(
                By.CLASS_NAME, "btn.w-50.next-button"
            )
            next_round_button.click()
        return True
    except NoSuchElementException:
        return False


def preprocess_vision(vision):
    return vision.split("-")[0].capitalize()


def preprocess_version(version):
    v = version.split("\n")
    if len(v) == 1:
        direction = ""
        version_number = v[0]
    else:
        direction, version_number = v
    return direction, float(version_number)


def guess_char(char_name, browser):
    search_input = browser.find_element(By.CLASS_NAME, "vs__search")
    search_input.clear()
    search_input.send_keys(char_name)
    search_input.send_keys(Keys.RETURN)


def preprocess_feature(feature):
    feature = feature.lower()
    if feature == "material":
        return "ascension_material"
    elif feature == "asc stat":
        return "ascension"
    elif feature == "weekly boss":
        return "weekly_boss"
    return feature


def filter_characters(filtered_df, round_data):
    ignore_features = ["photo"]

    for feature, (value, correct) in round_data.items():
        feature = preprocess_feature(feature)
        value = value.replace("_", " ")
        if feature in ignore_features:
            continue

        if feature == "version":
            direction, version_number = preprocess_version(value)
            filtered_df = filtered_df[
                filtered_df["version"].apply(
                    lambda x: compare_versions(x, direction, version_number)
                )
            ]
        else:
            if feature == "talents":
                value = value.capitalize()
            elif feature == "vision":
                value = value.split("-")[0].capitalize()

            if correct:
                filtered_df = filtered_df[filtered_df[feature] == value]
            else:
                filtered_df = filtered_df[filtered_df[feature] != value]
    return filtered_df


def compare_versions(row_version, direction, guessed_version):
    if pd.isnull(row_version):
        return False
    try:
        if "⬇" in direction:
            return row_version < guessed_version
        elif "⬆" in direction:
            return row_version > guessed_version
        else:
            return row_version == guessed_version
    except ValueError:
        return False


def solve(char_data, browser):
    filtered_data = char_data.copy()

    max_rounds = 5
    current_round = 0

    while current_round < max_rounds:
        if len(filtered_data) == 1:
            character_guess = filtered_data.iloc[0]["name"]
        else:
            character_guess = filtered_data.iloc[len(filtered_data) // 2]["name"]

        guess_char(character_guess, browser)

        if check_win(browser):
            return

        round_data = read_guess_table(browser)
        # print(round_data[-1])

        filtered_data = filter_characters(filtered_data, round_data[-1])
        # print(f"Filtered down to {len(filtered_data)} characters.")

        current_round += 1

    print("Max rounds reached without winning. Please check the strategy.")


def main():
    browser = webdriver.Firefox()

    browser.get("https://us.genshindle.com/endless")
    assert "Genshindle" in browser.title

    char_data = load_data()
    char_data = char_data.sort_values(by="version")

    while True:
        solve(char_data, browser)


if __name__ == "__main__":
    main()
