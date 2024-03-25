from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import Select
import pandas as pd
import re

driver = webdriver.Chrome()
driver.get('https://brokercheck.finra.org/')

print("This program will scan a given firm by ID and find all current employees.")
firm_id = input("Enter Firm ID: ")
exclude_address = input("Enter Street Address to Exclude: (Hit Enter again if none) (Example: 10150 Meanley Dr and 10150 M will yield the same result) ")

data = []

input_field = driver.find_element(By.CSS_SELECTOR, "input[formcontrolname='firmNameCrd']")
input_field.send_keys(firm_id)

search_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='IndividualSearch']")
search_button.click()

page_text_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'px-5')]//span[contains(text(), 'of') and contains(text(), 'page')]")))
page_text = driver.execute_script("return arguments[0].innerText;", page_text_element).strip()
page_num = re.search(r'\b\d+\s*of\s*(\d+)\s*pages?', page_text, re.IGNORECASE)
total_pages = int(page_num.group(1))

select_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//select[.//option[contains(text(), 'Sort by Name (A-Z)')]]")))
select_object = Select(select_element)
select_object.select_by_visible_text("Sort by Name (A-Z)")

for page in range(1, total_pages + 1):
    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "investor-tools-individual-search-result-template")))
    people = driver.find_elements(By.CSS_SELECTOR, "investor-tools-individual-search-result-template") #find twelve persons per page
    for index in range(len(people)):
        people = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "investor-tools-individual-search-result-template")))
        person = people[index]

        try:
            employment_section = WebDriverWait(person, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "investor-tools-search-results-current-employment"))) #find employment section
            employment_section_text = employment_section.text
            crd_number_match = re.search(r'CRD#:\s*(\d+)', employment_section_text)

            if crd_number_match and crd_number_match.group(1) == firm_id:
                    details_button = WebDriverWait(person, 10).until(EC.visibility_of_element_located((By.XPATH, ".//button[contains(., 'MORE DETAILS')]")))
                    details_button.click()

                    name_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "investor-tools-big-name div.flex > span.text-lg")))
                    name = name_element.text.strip()

                    address_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "investor-tools-address")))
                    full_address = address_element.get_attribute('innerText').strip() #gets full address even through page breaks
                    address_parts = [part.strip() for part in full_address.split('\n') if part.strip()]
                    if address_parts: #cuts off the +1
                        last_part = address_parts[-1]
                        address_parts[-1] = re.sub(r'\s*\+\d+$', '', last_part).strip()

                    person_info = {
                        "Name": name,
                        "Address 1": address_parts[0] if len(address_parts) > 0 else "",
                        "Address 2": address_parts[1] if len(address_parts) > 1 else ""
                    }
                    if exclude_address == "" or (exclude_address.lower() not in person_info["Address 1"].lower()):
                        data.append(person_info)
                        print(name)
                        print(full_address)
                        print(f"{name}\n{full_address}\n")

                    back_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Back")))
                    back_button.click()
                    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "investor-tools-individual-search-result-template")))
        except NoSuchElementException:
            print("Ran into an unexpected error, please try again.")
            continue
        
    next_button_xpath = "(//investor-tools-pager//button)[last()-1]" #based on the pager at the bottom, always 2nd to last button
    try:
        next_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, next_button_xpath)))
        next_button.click()
    except TimeoutException:
        print("Next page not found, unexpected error please try again.")
print("Total number of matches: " + str(len(data)))
df = pd.DataFrame(data)
df.to_excel(f"output{firm_id}.xlsx", index=False, header=True)
