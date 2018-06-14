from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException,TimeoutException
from time import sleep
from wdfi import wdfi
import random
import os
import csv
import sys
import time

wd = wdfi.wdfi()

yes_zip = ['53224', '53217', '53223', '53225', '53222', '53211', '53226', '53213', '53202', '53203', '53233', '53214',
           '53204',
           '53227', '53219', '53215', '53207', '53228', '53220', '53221', '53207', '53235', '53130', '53129', '53110',
           '53005',
           '53122', '53226', '53214', '53227', '53219', '53215', '53207', '53151', '53228', '53220', '53221', '53130',
           '53129',
           '53235', '53110', '53172', '53150', '53132', '53172', '53154', '53022', '53097', '53092', '53051', '53217']
maybe_zip = ['53223', '53209', '53212', '53224', '53223', '53209','53186','53072','53208','53086','53549','58104']
no_zip = ['53216', '53206', '53210', '53208', '53205', '53208', '53225', '53218']
llc_list = []

class Ccap(object):
    def run(self):
        print("Scraper Start...")
        count = 0
        start_time = time.time()
        # obtain local directory for chrome driver location
        cwd = os.getcwd()
        chrome_driver_url = str(cwd) + '\\chromedriver.exe'

        # setup file writer
        writer = open('C_Cap_INFO.csv', 'w')

        # Access Table Database
        url = "https://wcca.wicourts.gov/advanced.html"
        driver = webdriver.Chrome(executable_path=chrome_driver_url)
        driver.get(url)

        sleep(60)
        case_links = driver.find_elements_by_class_name("case-link")
        num_of_case_links = str(len(case_links))
        date_range_str = self.get_date_range(driver)
        lead_date_line = "Possible Leads: " + num_of_case_links + " Date Range: " + date_range_str + "\n"
        print(lead_date_line)

        # Writes out header lines
        writer.write(lead_date_line)
        writer.write("Defendant Address, Plaintiff Address, Plaintiff Name, ZipCode_Status \n")

        # Retrieve info from each case
        for case_link in case_links:

            count += 1
            skip = False
            # print(case_link)
            case_link = case_link.get_attribute('href')
            case_driver = webdriver.Chrome(executable_path=chrome_driver_url)
            try:
                case_driver.get(str(case_link))
            except TimeoutException as ex:
                print("Exception has been thrown. " + str(ex))
                case_driver.close()
                skip = True
            except:
                print("Exception has been thrown. ")
                case_driver.close()
                skip = True
            sleep(random.randint(1, 4))

            try:
                parties = case_driver.find_elements_by_class_name('party')
            except NoSuchElementException:
                skip = True
            except:
                skip = True

            if skip is not True:
                # Plaintiff
                plaintiff_party = None
                try:
                    plaintiff_party = parties[0]
                    plaintiff_name = self.get_plaintiff_name(plaintiff_party)
                    upcase_name = plaintiff_name.upper()
                    plaintiff_split = str(plaintiff_name).split(":")
                    plaintiff_name = plaintiff_split[1]
                    if "," in plaintiff_name:
                        p_name_split = plaintiff_split[1].split(",")
                        plaintiff_name = p_name_split[1] + p_name_split[0]

                    if "LLC" not in upcase_name:
                        # plaintiff address
                        p_address = self.get_plaintiff_party_non_llc_address(plaintiff_party)
                    else:
                        # lookup local
                        bool = self.llc_lookup(plaintiff_split[1])
                        if bool is False:
                            # lookup external
                            success = False
                            try_count = 0
                            info = []
                            # try looking up LLC information
                            while (not success):
                                try:
                                    info = wd.getRegAgent(plaintiff_split[1])
                                    success = True
                                except:
                                    # print("Lost WDFI connection, retrying")
                                    wd.getIdent()
                                    try_count = try_count + 1
                                    if (try_count >= 3):
                                        info = ["No record found", "No address found"]
                                        break

                            checker = "No record found"
                            if info[0] in checker:
                                llc_list.append(plaintiff_name[1])
                            # assign info to local vars
                            plaintiff_name = info[0]
                            p_address = info[1]
                        else:
                            plaintiff_name = "No record found"
                            p_address = "No address found"

                        p_address = self.remove_extra_whitespace(p_address)

                    # Defendant
                    defendant_party = parties[1]

                    d_address = self.get_defendant_address(defendant_party)

                    if count % 10 == 0:
                        elapsed_time = time.time() - start_time
                        elapsed_time = elapsed_time / 60
                        print(str(count) + " " + str(int(elapsed_time)) + " mins")

                    self.write_line(writer, d_address, p_address, plaintiff_name.strip())
                except IndexError:
                    print("Case Closed")
                except:
                    print("Error: Case Closed")
                # close browser each time
                case_driver.close()

        # close file writer
        writer.close()
        print("End of Read")
        sys.exit()

    # returns "YES"/"MAYBE"/"NO"/"NOT AVAILABLE"
    def zip_lookup(self, address):
        if address is "No Address":
            return "NOT AVAILABLE"

        address = address.strip()
        address_split = address.split(" ")
        index = 0
        us_phrase = address[-3:]
        if "US" in us_phrase:
            index = len(address_split) - 2
        else:
            index = len(address_split) - 1
        zip = address_split[index]
        zip = zip.strip()
        # print(zip)
        if zip in yes_zip:
            return "YES"
        elif zip in maybe_zip:
            return "MAYBE"
        elif zip in no_zip:
            return "NO"
        else:
            return "NOT AVAILABLE"

    # takes in information required to write out a properly formatted line
    def write_line(self, file, d_address, p_address, p_name):
        zip = self.zip_lookup(d_address)
        line = d_address + "," + p_address + "," + p_name + "," + zip + "\n"
        print(line)
        file.write(line)

    # Using the party Web Element, returns the plaintiff party non llc info.
    def get_plaintiff_party_non_llc_address(self, party):
        p_address = ""
        try:
            p_address_element = party.find_element_by_class_name("columns")
            p_address_element = p_address_element.find_element_by_tag_name("dd")
            p_address = p_address_element.get_attribute('innerHTML')
            p_address = p_address.replace(",", "")
            p_address = self.remove_extra_whitespace(p_address)
        except NoSuchElementException:
            p_address = "No Address"
        except:
            p_address = "No Address"
        return p_address

    # Using the party Web Element, returns the plaintiff name info.
    def get_plaintiff_name(self, party):
        plaintiff_name = ""
        try:
            p_name_element = party.find_element_by_class_name("detailHeader")
            plaintiff_name = p_name_element.get_attribute('innerHTML')
            plaintiff_name = plaintiff_name.replace("&amp;", "&")
        except NoSuchElementException:
            plaintiff_name = "No Record Found"
        except:
            plaintiff_name = "No Record Found"
        return plaintiff_name

    # Using the party Web Element, returns the defendant address info.
    def get_defendant_address(self, party):
        d_address = ""
        try:
            d_address_element = party.find_element_by_class_name("columns")
            d_address_element = d_address_element.find_element_by_tag_name("dd")
            d_address = d_address_element.get_attribute('innerHTML')
            d_address = d_address.replace(",", "")
        except NoSuchElementException:
            d_address = "No Address"
        except:
            d_address = "No Address"
        return d_address

    # Using the party Web Element, returns the defendant name info.
    def get_defendant_name(self, party):
        defendant_name = ""
        try:
            d_name_element = party.find_element_by_class_name("detailHeader")
            defendant_name = d_name_element.get_attribute('innerHTML')
            name = defendant_name.replace("&amp;", "&")
            removed_title = str(name).split(":")
            reverse_name_split = removed_title[1].split(",")
            defendant_name = reverse_name_split[1] + reverse_name_split[0]
        except NoSuchElementException:
            return "No Record Found"
        except:
            return "No Record Found"

        return defendant_name

    # Removes additional whitespace from a string and returns it
    def remove_extra_whitespace(self, str):
        str = str.replace("  ", "")
        str = str.rstrip()
        return str

    # Returns the date range string acquired from the initial table database page
    def get_date_range(self, driver):
        date_range = ""
        try:
            element = driver.find_element_by_xpath("/html/body/div/div/div/main/div/span/span/span[3]")
            text = element.get_attribute('innerHTML')
            index = text.rfind(">")
            date_range = text[index + 1:]
            # print(date_range)
        except NoSuchElementException:
            date_range = "Date Range Not Found"
        except:
            date_range = "Date Range Not Found"
        return str(date_range)

    def llc_lookup(self,llc_name):
        if llc_name in llc_list:
            return True
        else:
            return False


if __name__ == '__main__':
    Ccap().run()
