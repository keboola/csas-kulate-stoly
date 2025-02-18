# Streamlit Aplikace - Kulaté stoly

Tento projekt představuje Streamlit aplikaci, která umožňuje uživatelům pracovat s daty uloženými ve Snowflake v Keboola prostředí. 
Aplikace slouží při průběhu a k zpracování dat Kulatých stolů.

## Hlavní specifikace aplikace
- Lokalizace: CZ
- Uživatelské role: BP, MA, LC, DEV, TEST
- Fáze performance managementu: Kalibrace manažerských hodnocení během Kulatých stolů

### Obecné vlastnosti

- **Organizační struktura**: Aplikace zobrazuje aktuální strukturu dle práv přihlášeného uživatele a jeho role.
- **Hodnocení zaměstnanců**: Více hodnocení ročně, s možností následné kalibrace.
- **Data-driven**: Všechny operace řízené daty, minimum logiky v kódu.
- **Filtrace**: Možnost filtrovat dle jednotlivých manažerů, profese či jednotlivců.
- **Grafické zobrazení**: Hodnocení vizualizováno v grafech.
- **Kalibrace**: Proces kalibrace hodnocení během speciálních schůzek.
- **Uzamykání výsledků**: Business partner může uzamknout hodnocení, což manažerům zabrání v dalších editacích.

### Uživatelské role

#### Business Partner (BP)
- **Přístup**:
  - Přístup ke všem datům.
- **Možnosti editace**:
  - Možnost editace vybraných polí u všech záznamů, ke kterým má přístup, a které nejsou uzamčené nebo jsou uzamčené méně než 30 dní.
  - Možnost zamknutí záznamů. BP má stále oprávnění ke změnám, ale pouze 30 dní od uzamčení.
- **Vizualizace**:
  - **Tabulka**: Zobrazuje filtrovatelný seznam zaměstnanců, hodnoty jejich hodnocení a stav zamčení. BP může editovat hodnoty hodnocení.
  - **Grid 5x5**: Vizualizace jmen zaměstnanců podle hodnot “CO” a “JAK”; pohled vždy filtrován filtry zvolenými u vizualizace “Tabulka.”
  - **Grid 3x3**: Vizualizace podle hodnot “CO a JAK” a “POTENCIÁL”; pohled vždy filtrován filtry zvolenými u vizualizace “Tabulka.”
  - **Trendový graf**: Sloupcový graf pro hodnoty “CO” a “JAK” z posledních N období pro vybranou skupinu zaměstnanců; zobrazené hodnoty jsou průměrem vyfiltrované skupiny.
- **Ukládání filtrů**:
   - Možnost uložit aktuálně zvolené filtry. Možnost načíst dříve uložené filtry pro rychlejší manipulaci s daty.
- **Generování CSV**:
   - Možnost vygenerovat a uložit CSV soubor.   

#### Manažer (MA)
- **Přístup**:
  - Přístup k zaměstnancům ve struktuře svých přímých i nepřímých podřízených.
- **Možnosti editace**:
  - Možnost editace pouze přímých podřízených, ne podřízených svých podřízených.
- **Vizualizace**:
  - Stejný přístup jako BP ke všem vizualizacím.
- **Funkcionalita 1on1**:
  - Možnost aktivace módu pro setkání se zaměstnancem, kde se citlivé údaje na vizualizacích anonymizují, kromě vybraného zaměstnance.
  - Tato funkcionalita je aplikována pouze na zobrazení vizualizací typu Grid.
- **Ukládání filtrů**:
   - Možnost uložit aktuálně zvolené filtry. Možnost načíst dříve uložené filtry pro rychlejší manipulaci s daty.
- **Generování CSV**:
   - Možnost vygenerovat a uložit CSV soubor.

#### Leaders and Culture (LC)
- **Přístup**:
  - Přístup ke všem datům včetně historie.
- **Omezení**:
  - Nemají oprávnění k editaci ani k zamykání záznamů.
  - Nemají přístup k funkci 1on1.
- **Ukládání filtrů**:
   - Možnost uložit aktuálně zvolené filtry. Možnost načíst dříve uložené filtry pro rychlejší manipulaci s daty.
- **Generování CSV**:
   - Možnost vygenerovat a uložit CSV soubor.

#### DEV a TEST 
Tyto role mají přístup ke všem datům a funkcionalitám, mohou je editovat a mají možnost odemykat uzamčené záznamy.
Role mají možnost vstoupit do jakékoliv jiné role - to jim dává možnost testovat funkcionality konkrétní role a konkrétního uživatele.


## Struktura projektu

### Hlavní soubor aplikace
- **app.py**: Hlavní soubor aplikace, který inicializuje prostředí, načítá data, a zobrazuje jednotlivé komponenty a UI prvky dle rolí uživatele. 

### Moduly

- **data_manager_snowflake.py**: Poskytuje funkce pro načítání, ukládání a správu dat ve Snowflake.
- **chart_manager.py**: Obsahuje funkce pro předzpracování dat a generování grafů a tabulek, které zobrazují výkonnostní metriky.
- **filter_manager.py**: Spravuje funkce pro ukládání, načítání a aplikování filtrů pro daného uživatele.
- **grid_manager.py**: Nastavuje AgGrid tabulku s konkrétními nastaveními pro zobrazení, úpravy a formátování buněk v závislosti na roli uživatele.


## Detailní popis kódu hlavního souboru aplikace
Funkce `main()` je hlavní vstupní bod aplikace. Zajišťuje inicializaci prostředí, načítání dat, správu rolí uživatelů a vykreslení uživatelského rozhraní. Níže je detailní popis logiky kódu:

### 1. Inicializace `session_state`
Funkce initialize_session_state() inicializuje všechny proměnné uložené v st.session_state na jejich výchozí hodnoty. Tím se předchází chybám při pokusu o přístup k neinicializovaným proměnným během běhu aplikace.

### 2. Načtení role uživatele a e-mailu
- **Načítání role uživatele:** Pomocí `headers` z Keboola API načítáme role uživatele.
- **Mapování rolí:** `role_mapping` převádí ID rolí na srozumitelné názvy jako `"BP"`, `"LC"`, `"MA"` atd.
- **Kontrola role:** Pokud role není rozpoznána, aplikace zobrazí varování a zastaví běh pomocí `st.stop()`.

### 3. Načtení dat
- **Kontrola, zda jsou data již načtena:** Pokud je datový rámec (`df`) prázdný, načteme data.
- **Načtení dat ze Snowflake:** Funkce `read_data_snowflake` načte data z tabulky ve Snowflake a uloží je do `session_state['df']`.

### 4. Režim pro vývojáře a testery
- **Povolení změny uživatele a role:** Umožňuje vývojářům a testerům simulovat různé uživatele a role.
- **Funkce `on_user_email_change`:** Aktualizuje filtry při změně e-mailu uživatele.

### 5. Načtení uložených filtrů

- **Kontrola a načtení filtrů:** Pokud nejsou filtry načteny, načtou se ze Snowflake na základě e-mailu uživatele.


### 6. Zobrazení hlavičky aplikace

- **Zobrazení informací o přihlášeném uživateli:** V hlavičce aplikace je zobrazen e-mail uživatele.

### 7. Definice záložek

- **Rozdělení aplikace do tří hlavních sekcí:**
  - **Editace:** Umožňuje uživateli upravovat data.
  - **Vizualizace:** Zobrazuje grafy a vizualizace.
  - **O aplikaci:** Poskytuje informace o aplikaci.

### 8. Logika záložky "Editace"

#### a) Filtrování dat
- **Výběr uloženého filtru:**  
  Uživatel si může vybrat uložený filtr pro zobrazení dat.

#### b) Aplikace filtrů na data
- **Filtrování datového rámce:**  
  Funkce `filter_dataframe` aplikuje vybrané filtry na data.

#### c) Úprava dat v tabulce (AgGrid)

AgGrid umožňuje uživatelům upravovat data podle jejich role a stavu zámku (`IS_LOCKED`). Následující pravidla a nastavení upravují chování:

- **Editovatelné sloupce:**  
  Uživatelé mohou upravovat pouze předem definované sloupce, které jsou označeny jako editovatelné.

- **Stylizace buněk:**  
  - Zamknuté řádky (`IS_LOCKED = 1`) mají šedé pozadí a nejsou upravitelné.
  - Pokud se hodnoty ve sloupcích `HODNOTY` nebo `VYKON` liší od jejich systémových hodnot (`HODNOTY_SYSTEM`, `VYKON_SYSTEM`) a řádek není zamknutý, buňky se zvýrazní oranžovou barvou.
  - Editovatelné buňky mají tučný text a černou barvu.

- **Nastavení na základě rolí:**
  - **Role `BP`:**  
    Řádky lze upravovat, pokud nejsou zamknuté (`IS_LOCKED = 0`) nebo byly zamknuty méně než 30 dní zpět. 
  - **Role `MA`:**  
    Uživatel může upravovat pouze ty řádky, kde je uveden jako přímý nadřízený (`DIRECT_MANAGER_EMAIL`).
  - **Role `LC`:**  
    Uživatelé s touto rolí nemohou upravovat žádné buňky.
  - **Role `DEV` a `TEST`:**  
    Mají přístup k plné editaci všech řádků a sloupců.

- **Interaktivní prvky:**  
  Některé sloupce, například `HODNOTY`, `VYKON`, `POTENCIAL`, a další, používají výběrové seznamy pro zajištění konzistentních hodnot při úpravách.

- **Pinning důležitých sloupců:**  
  Sloupce jako `FULL_NAME` a `DIRECT_MANAGER_FULL_NAME` jsou fixovány na levé straně tabulky pro lepší přehlednost.

#### d) Akční kroky po úpravách
Po úpravě dat v tabulce lze změny uložit pomocí tlačítek, která jsou dostupná podle role uživatele:
- **Uložení změn:**  
  Změny jsou uloženy do databáze.


### 9. Logika záložky "Vizualizace"

- **Pro manažery ('MA'):**  
  Mohou si vybrat konkrétního zaměstnance pro zobrazení vizualizací pro schůzky 1-on-1.
- **Pro ostatní role:**  
  Zobrazují se vizualizace pro aktuálně filtrovaná data.


### 10. Logika záložky "O aplikaci"

- **Zobrazení informací o aplikaci:**  
  Stylizovaný text s odkazem na manuál na Confluence.


### 11. Spuštění aplikace

- **Kontrola, zda je skript spuštěn jako hlavní program:**  
  Pokud ano, zavolá se funkce `main()`.

## Rychlý start - pro vývojáře

1. **Nastavení**: Upravte `st.secrets` se správnými přihlašovacími údaji a konfiguračními údaji pro přístup k Snowflake a Keboola.

2. **Spuštění aplikace**:
   ```bash
   streamlit run app.py
   ```

### Role uživatelů
Uživatelé jsou rozděleni do několika rolí (`BP`, `MA`, `LC`, `DEV`, `TEST`), které určují oprávnění k editaci a viditelnost jednotlivých funkcí.

### Správa Filtrů
Uživatelé mohou vytvářet a ukládat filtry pro specifické zobrazení dat a načítat uložené filtry.

### Zobrazení a úprava dat
Data jsou zobrazena v AgGrid s možnostmi úprav, filtrací a sledování změn.

## Příklady Použití

### Uložení a načtení filtru

**Editace hodnot:**
1. Pomocí filtrů zvolte záznamy, které chcete editovat
2. Proveďte potřebné změny v jednotlivých sloupcích
3. Po provedení změn potvrďte jejich uložení tlačítkem Potvrdit uložení změn.

**Pro uložení vlastního filtru v aplikaci:**
1. Nastavte požadované filtry.
2. Vyberte možnost "Uložit filtr".
3. Vložte název filtru a potvrďte uložení.

**Pro načtení uloženého filtru:**
1. Vyberte uložený filtr z dostupných možností.
2. Aplikujte filtr na zobrazená data.

### Vizualizace výkonu a potenciálu
Po výběru filtru a nastavení specifických kritérií můžete zobrazit 5x5 a 3x3 mřížky a sloupcové grafy pro sledování trendů výkonu a potenciálu.

## Autor a Kontakt
Problémy a dotazy zasílejte prosím správci projektu.
Autor první verze aplikace je michal.hruska@keboola.com



## Detailní popis funkcí jednotlivých částí scriptu

### app.py

**`initialize_session_state()`**
Inicializuje výchozí hodnoty `session_state` proměnných používaných v aplikaci.

---

**`process_and_save_changes(df, changed_rows, debug)`**
Zpracovává změněné řádky, které poté ukládá do Snowflake.

---

**`filter_dataframe(filter_model, selected_year, toggle)`**
Filtrování datového rámce na základě vybraných filtrů, roku a nastavení toggle (např. pouze tým uživatele).

---

**`main()`**
Hlavní funkce aplikace, která nastavuje prostředí, zpracovává role uživatelů a vykresluje uživatelské rozhraní (tabulky, filtry, grafy).


### data_manager_snowflake.py


#### `get_snowflake_session(client)`
Vytvoří a vrátí Snowflake session pomocí Snowpark. Zajišťuje opakovaně použitelnou session uloženou v `session_state`.

---

#### `read_data_snowflake(table_id, client)`
Načte data ze Snowflake tabulky do Pandas DataFrame, aplikuje transformace a výsledek uloží do `session_state`. 

---

#### `execute_query_snowflake(query, client)`
Provede SQL dotaz ve Snowflake pomocí Snowpark.

---

#### `write_data_snowflake(df, table_name, auto_create_table=False, overwrite=False, client)`
Zapíše Pandas DataFrame do Snowflake tabulky s volitelnou automatickou tvorbou tabulky a funkcionalitou přepsání.

---

#### `map_json_to_snowflake_type(json_type)`
Mapuje JSON datové typy na odpovídající datové typy ve Snowflake. Podporované typy zahrnují:
- `str`: Mapuje na `VARCHAR(16777216)`
- `int`: Mapuje na `NUMBER(38,0)`
- `datetime64[ns]`: Mapuje na `TIMESTAMP_NTZ(9)`

---

#### `save_changed_rows_snowflake(df_original, changed_rows, debug, client, progress)`
Ukládá pouze změněné řádky do CSV souboru (pro debugování) nebo do Snowflake tabulky. Zajišťuje validaci schématu, logování a dočasné zpracování pro bezpečné aktualizace. Zahrnuje:
- Sloučení původních a změněných řádků.
- Validaci vůči očekávanému schématu.
- Zápis do Snowflake pomocí dočasné tabulky.
- Zajištění správného formátování primárních klíčů, časových razítek a dalších datových polí.


### chart_manager.py


#### `preprocess_df_for_charts(df)`
Připraví DataFrame pro vykreslení grafů:
- Převádí datové typy na odpovídající formáty.
- Přidává chybějící kombinace hodnot JAK, CO a POTENCIAL.

---

#### `categorize_3_grid(row)`
Kategorizuje řádky podle kombinací hodnot JAK, CO a POTENCIAL do kategorií:
- **Top**
- **Middle**
- **Low**
- **Nehodnocení**

---

#### `categorize_5_grid(row)`
Kategorizuje řádky podle kombinací hodnot JAK a CO pro 5x5 mřížku do kategorií:
- **Top**
- **Middle**
- **Low**
- **Nehodnocení**

---

#### `display_5_grid_summary(filtered_df, period)`
Zobrazuje souhrn kategorií pro 5x5 mřížku:
- **Kategorie:** Top, Middle, Low, Nehodnocení
- Počet a procentuální zastoupení.

---

#### `display_3_grid_summary(filtered_df, period)`
Zobrazuje souhrn kategorií pro 3x3 mřížku:
- **Kategorie:** Top, Middle, Low, Nehodnocení
- Počet a procentuální zastoupení.

---

#### `display_5_grid(filtered_df, period)`
Zobrazuje 5x5 mřížku kombinací JAK (hodnoty) a CO (výkonu):
- Interaktivní mřížka vytvořená pomocí AgGrid.
- Obsahuje barevné zvýraznění na základě hodnocení.

---

#### `display_3_grid(filtered_df, period)`
Zobrazuje 3x3 mřížku kombinací JAK, CO a POTENCIAL:
- Interaktivní mřížka vytvořená pomocí AgGrid.
- Obsahuje barevné zvýraznění podle kombinací hodnot.

---

#### `display_column_chart(df, filtered_df)`
Zobrazuje sloupcový graf trendů hodnocení CO a JAK v čase:
- Sleduje průměrné hodnocení CO a JAK pro jednotlivé roky.
- Vizualizace je vytvořena pomocí knihovny Plotly.

---

#### `display_charts(df, filtered_df)`
Vykresluje všechny hlavní grafy:
- **5x5 mřížka:** Výkon a hodnoty (CO a JAK).
- **3x3 mřížka:** Výkon, hodnoty a potenciál (CO, JAK, POTENCIAL).
- **Trendový graf:** Vývoj CO a JAK hodnocení v čase.


### grid_manager.py


#### `setup_aggrid(df, editable_columns, columns_to_display, user_role, user_email)`
Konfiguruje AgGrid s následujícími funkcionalitami:
- **Editovatelnost:** Nastavuje sloupce, které lze upravovat, na základě uživatelské role a podmínek, jako je stav zamknutí (`IS_LOCKED`).
- **Formátování buněk:** 
  - Barevné zvýraznění pro zamknuté buňky a sloupce s odlišnými hodnotami (např. `HODNOTY`, `VYKON`).
  - Stylizace a fixace důležitých sloupců (`FULL_NAME`, `DIRECT_MANAGER_FULL_NAME`).
- **Zobrazené sloupce:** Filtruje a přizpůsobuje sloupce podle parametrů aplikace.
- **Role specifická nastavení:**
  - **BP:** Upravitelnost založená na zamknutí a datu poslední změny.
  - **MA:** Upravitelnost omezená na řádky, kde je uživatel přímým manažerem.
  - **LC:** Žádná editovatelnost.
  - **DEV/TEST:** Plná editovatelnost všech sloupců.
- **Interaktivní prvky:** 
  - Přidává výběrové seznamy (`agSelectCellEditor`) do sloupců, jako je `HODNOTY` a `VYKON`.

---

#### `display_table(input_df, grid_options, grid_key)`
Zobrazuje AgGrid tabulku s následujícími funkcemi:
- **Sledování změn:** 
  - Porovnává aktuálně upravená data s posledním uloženým stavem (`df_last_saved`) a identifikuje změny.
  - Sleduje pouze relevantní sloupce a ignoruje systémové informace (`HIST_DATA_MODIFIED_BY`, `HIST_DATA_MODIFIED_WHEN`, `LOCKED_TIMESTAMP`).
- **Uložení stavu:**
  - Uchovává originální data (`df_original`) a poslední uložená data (`df_last_saved`) pro zpětnou kontrolu.
- **Interaktivita:** 
  - Zajišťuje živé aktualizace a responzivní chování při změnách uživatele.
- **Výstup:** 
  - Vrací filtrovaná data, seznam změněných řádků a odpověď z AgGrid (`grid_response`).

### filter_manager.py

---

#### `apply_filter(df, filter_model)`
Aplikuje zadaný model filtru na DataFrame:
- Prochází sloupce ve filtru a aplikuje kritéria pomocí metody `isin`.
- Vrací DataFrame obsahující pouze řádky splňující filtr.

---

#### `save_filter_dialog_snowflake(filter_model)`
Zobrazuje dialog pro uložení filtru se zadaným modelem filtru. Momentálně se zaměřuje na interaktivní funkcionalitu ukládání filtrů.

---

#### `load_saved_filters_snowflake(user_email)`
Načítá uložené filtry pro daného uživatele ze Snowflake. Zajišťuje, že filtry jsou dostupné v aplikaci.

---

#### `save_current_filters_snowflake(user_email, filter_name, current_filter_model, progress_bar)`
Ukládá aktuální model filtru s metadaty (jméno filtru, e-mail uživatele) a sleduje průběh operace.




