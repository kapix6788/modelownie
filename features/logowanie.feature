Feature: Logowanie do systemu warsztatu

  Scenario: Poprawne logowanie klienta
    Given Użytkownik jest na stronie logowania
    When Wpisuje email "klient@test.pl" i hasło "tajne"
    And Klika przycisk zaloguj
    Then Zostaje przekierowany do panelu klienta