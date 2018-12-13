from .Scraper import Scraper
from .ConnectionScraper import ConnectionScraper
import json
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException

import time
from .Profile import Profile
from .utils import AnyEC


class ProfileScraper(Scraper):
    """
    Scraper for Personal LinkedIn Profiles. See inherited Scraper class for
    details about the constructor.
    """

    def scrape(self, url='', user=None):
        self.load_profile_page(url, user)
        return self.get_profile()

    def load_profile_page(self, url='', user=None):
        """Load profile page and all async content

        Params:
            - url {str}: url of the profile to be loaded
        Raises:
            ValueError: If link doesn't match a typical profile url
        """
        if user:
            url = 'http://www.linkedin.com/in/' + user
        if 'com/in/' not in url:
            raise ValueError("Url must look like ...linkedin.com/in/NAME")
        self.current_profile = url.split(r'com/in/')[1]
        self.driver.get(url)
        # Wait for page to load dynamically via javascript
        try:
            myElem = WebDriverWait(self.driver, self.timeout).until(AnyEC(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '.pv-top-card-section')),
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '.profile-unavailable'))
            ))
        except TimeoutException as e:
            raise ValueError(
                """Took too long to load profile.  Common problems/solutions:
                1. Invalid LI_AT value: ensure that yours is correct (they
                   update frequently)
                2. Slow Internet: increase the timeout parameter in the Scraper constructor""")
        print(self.driver.page_source)
        # Check if we got the 'profile unavailable' page
        try:
            self.driver.find_element_by_css_selector('.pv-top-card-section')
        except:
            raise ValueError(
                'Profile Unavailable: Profile link does not match any current Linkedin Profiles')
        # Scroll to the bottom of the page incrementally to load any lazy-loaded content
        self.scroll_to_bottom()

    def get_profile(self):
        try:
            profile = self.driver.find_element_by_id(
                'profile-wrapper').get_attribute("outerHTML")
        except:
            raise Exception(
                "Could not find profile wrapper html. This sometimes happens for exceptionally long profiles.  Try decreasing scroll-increment.")
        contact_info = self.get_contact_info()
        return Profile(profile + contact_info)

    def get_contact_info(self):
        try:
            # Scroll to top to put clickable button in view
            self.driver.execute_script("window.scrollTo(0, 0);")
            button = self.driver.find_element_by_css_selector(
                '.pv-top-card-v2-section__contact-info')
            button.click()
            contact_info = self.wait_for_el('.pv-contact-info')
            return contact_info.get_attribute('outerHTML')
        except Exception as e:
            print(e)
            return ""

    def get_mutual_connections(self):
        try:
            link = self.driver.find_element_by_partial_link_text(
                'Mutual Connection')
        except NoSuchElementException as e:
            print("NO MUTUAL CONNS")
            return []
        with ConnectionScraper(scraperInstance=self) as cs:
            cs.driver.get(link.get_attribute('href'))
            cs.wait_for_el('.search-s-facet--facetNetwork form button')
            return cs.scrape_all_pages()
