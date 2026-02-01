import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "http://127.0.0.1:5000"


def run_functional_test():
    print("START TESTU FUNKCJONALNEGO")
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        rand_id = random.randint(1000, 9999)
        email = f"auto_user_{rand_id}@test.pl"
        password = "haslo1234"
        name = "RobotSelenium"

        #REJESTRACJA
        print(f"\n[1/3] Próba rejestracji użytkownika: {email}")
        driver.get(f"{BASE_URL}/register")
        time.sleep(1)

        driver.find_element(By.NAME, "first_name").send_keys(name)
        driver.find_element(By.NAME, "last_name").send_keys("Automatyczny")
        driver.find_element(By.NAME, "email").send_keys(email)
        driver.find_element(By.NAME, "password").send_keys(password)
        try:
            driver.find_element(By.NAME, "phone_number").send_keys("123456789")
        except:
            pass
        try:
            driver.find_element(By.NAME, "role").send_keys("client")
        except:
            pass

        submit_btn = driver.find_element(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
        submit_btn.click()
        print(" -> Formularz wysłany.")
        time.sleep(2)

        #LOGOWANIE
        print(f"\n[2/3] Próba logowania na nowe konto...")
        driver.get(f"{BASE_URL}/login")
        time.sleep(1)

        driver.find_element(By.NAME, "email").send_keys(email)
        driver.find_element(By.NAME, "password").send_keys(password)

        login_btn = driver.find_element(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
        login_btn.click()
        time.sleep(2)

        #WERYFIKACJA
        print(f"\n[3/3] Weryfikacja sukcesu...")
        page_source = driver.page_source
        current_url = driver.current_url
        success = False
        if "Wyloguj" in page_source or "/panel" in current_url:
            success = True

        if success:
            print("✅ SUKCES: Zalogowano poprawnie do panelu!")
            print(f"   Aktualny URL: {current_url}")
        else:
            print("❌ BŁĄD: Nie udało się zalogować.")
            print("   Sprawdź, czy serwer Flask jest uruchomiony!")

    except Exception as e:
        print(f"\n❌ WYJĄTEK KRYTYCZNY: {e}")
    finally:
        print("\n Koniec testu")
        time.sleep(5)
        driver.quit()


if __name__ == "__main__":
    run_functional_test()