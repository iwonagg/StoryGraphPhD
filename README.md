# Implementacja referencyjna systemu StoryGraph
![plot](./images/ikonaSG.png)
<span style="color:red">**toryGraph**</span> to projekt modelu formalnego pozwalający zapisać strukturę narracyjną gry fabularnej w postaci modelu grafowego. Fabuła gry przedstawiona 
jest w postaci grafu stanu świata i produkcji pozwalających go modyfikować. Produkcje dotyczące działań ogólnych 
dowolnych postaci (chodzenie, podnoszenie przedmiotów, pozyskiwanie wiedzy itp.) zebrane są w zbiorze produkcji 
generycznych. Produkcje bardziej szczegółowe dla wygody projektantów podzielone są na misje.
Model grafowy opiera się na grafie warstwowym z czterema warstwami: lokacji („Locations”), postaci („Characters”), 
przedmiotów („Items”) oraz informacji fabularnych („Narration”).

Implementacja referencyjna demonstruje możliwości modelu i pozwala obejrzeć rozwiązania implementacyjne zalecane przez twórców systemu. Może też służyć jako silnik narracyjny dla zewnętrznych projektów dzięki udostępnionemu API.

## Co da się zrobić w tym projekcie?
Zbiór skryptów w języku python dostępny w tym repozytorium pozwala na:
- symulację rozgrywki: modyfikację wczytanego świata w trybie decyzji użytkownika: przeprowadzenie procesu decyzyjnego od początku do końca, 
gry i wizualizację pośrednich stanów świata,
- modyfikację wczytanego świata w trybie projektowym: arbitralne dodawanie, usuwanie i modyfikowanie węzłów,
- sprawdzenie poprawności plików `.json` zawierających światy i produkcje (lokalnie lub poprzez API),
- wygenerowanie poglądowych schematów produkcji (lokalnie lub poprzez API),
- wygenerowanie schematu dziedziczenia produkcji.

## Przykładowe uruchomienia
- Przejście misji DragonStory
  - uruchom skrypt `production_processor/application`. Przejdź misję zgodnie z którąś ścieżką ze schematu [examples/DragonStory/diagram_misji/quest_desing_diagram.png](https://github.com/iwonagg/StoryGraphPhD/blob/master/examples/DragonStory/diagram_misji/quest_desing_diagram_resize.png) lub zaproponuj własną ścieżkę. 
   
     &#127909; **[Nagranie uruchomienia przejścia misji](https://ujchmura-my.sharepoint.com/:v:/g/personal/iwona_grabska_uj_edu_pl/EdI_93ZtQStGs7uTn9qqSOoB6lz3XZmIfjK-b_3ux1I5aw?e=cFal8r)**
- Wizualizacja drzewa hierarchii produkcji
  - uruchom skrypt `production_hierarchy/visualise_production_hierarchy`. Plik wynikowy znajdziesz w katalogu `visualisation/out_hierarchy_new`.
- Testowanie przesłaniania produkcji
  - uruchom skrypt `production_processor/application`. Idź do więzienia lub wypij zatruty alkohol kupiony od pijaka. Należy pamiętać, że w trybie testerskim użytkownik jest informowany o przesłonięciu produkcji, ale nadal może ją wykonać.
    
    &#127909; **[Nagranie uruchomienia testowania przesłonięć](https://ujchmura-my.sharepoint.com/:v:/g/personal/iwona_grabska_uj_edu_pl/EUumkkDChO5NhiycIe1FcXwB9GVwWizlUqxyVmRDs7ITyg?e=fwZD9a)**
- Przejście misji RumcajsStory
  - w skrypcie `production_processor/application` w bloku definicji (linie 30-38) zmień domyślne wartości na:
  `world_name = 'world_RumcajsStory'`, `quest_names = ['quest_RumcajsStory_close']`, `character_name = 'Rumcajs'`
  - uruchom skrypt `production_processor/application`. Przejdź misję zgodnie z którąś ścieżką ze schematu [examples/RumcajsStory/diagram_misji/Rumcajs_szczegółowy.png](https://github.com/iwonagg/StoryGraphPhD/blob/master/examples/RumcajsStory/diagram_misji/Rumcajs_szczegółowy_resize.png)

## Specyfikacja
 - [Specyfikacja StoryGraph 1.2](Specyfikacja_StoryGraph_01.2_official.pdf)
 - [Dodatek A – Definicje modelu formalnego](Dodatek_A_do_specyfikacji_Definicje_modelu_grafowego.pdf)
 - [Dodatek B – JSON schema](./json_validation/json_schema/schemas/schema_updated_20220213.json)


## Potrzebne dane źródłowe
W katalogu materiałów projektowych (wskazanym w pliku `config.py`, domyślnie katalog `examples`);
- co najmniej jeden plik `.json` misji, mogą być pogrupowane w podkatalogi. Zazwyczaj dla misji mamy dwa pliki, jeden zawierający produkcje generyczne a drugi szczegółowe;

[comment]: <> (- podkatalog: `schema`, plik ze schematem poprawnej struktury JSON &#40;bieżący to: `schema_updated_najnowszadata.json`&#41;;)
- co najmniej jeden plik `.json` świata.

W repozytorium skryptów:
- podkatalog: `json_validation/allowed_names`: pliki `.json` z dozwolonymi nazwami węzłów z czterech warstw.

[comment]: <> (## Jak go uruchomić?)

[comment]: <> (Potrzebny jest Python 3.8.)

[comment]: <> (1. Wymagane jest wskazanie katalogów źródłowych z plikami `.json` zawierającymi światy i produkcje.)

[comment]: <> (Ścieżka lokalna do plików na dysku użytkownika musi znaleźć się w pliku `config.py` w katalogu `config`. Na podstawie )

[comment]: <> (pliku `config.dist.py` należy stworzyć plik `config.py` z właściwą ścieżką lokalną do katalogu, w którym umieściliśmy )

[comment]: <> (pliki `.json`. Nie musi to być katalog, w którym jest repozytorium.)

[comment]: <> (2. Należy stworzyć środowisko uruchomieniowe:)

[comment]: <> ( &#40;komendy powinno się uruchamiać w katalogu projektu&#41;)

[comment]: <> ( * `python3 -m venv .venv`)

[comment]: <> ( * `source .venv/bin/activate`)

[comment]: <> (3. Następnie wykonać instrukcję:)

[comment]: <> (* `pip install -r requirements.txt`)

[comment]: <> (4. A na końcu uruchomić skrypt:)

[comment]: <> (* `production_processor/application.py` – aby przeprowadzić symulację procesu decyzyjnego gracza)

[comment]: <> (* `manual_word_modification/word_modification.py` – aby tworzyć lub modyfikować świat)

[comment]: <> (* lub inny w miarę potrzeb.)

## Jak go uruchomić? 

### Wymagania
- zainstalowany Python przynajmniej w wersji 3.8
- PyCharm lub inne IDE
- [GraphViz](https://graphviz.org/download/) w wersji przynajmniej 2.50
  - przy instalacji na windows wybierz "Add Graphviz to system PATH for all users" lub "Add Graphviz to system PATH for current users"

### Instalacja i przygotowanie projektu
- pobierz projekt (`Git / Clone...`) z repozytorium GitHub (`https://github.com/iwonagg/StoryGraphPhD.git`)
- stwórz wirtualne środowisko (venv)
  - szczegółowa instrukcja dla PyCharm:
    - otwórz `File / Settings / Project: StoryGraph / Python interpreter`
    - koło zębate i `Add...`
    - wybierz interpreter Pythona w wersji przynajmniej 3.8 i stwórz nowe wirtualne środowisko w katalogu `venv` w projekcie
- zainstaluj pakiety projektu
  - szczegółowa instrukcja dla PyCharm:
    - otwórz `Terminal`
      - wykonaj `pip install -r requirements.txt`
- stwórz nowy plik kopiując plik `config/config.dist.py` do `config/config.py`
- jeżeli chcesz korzystać z innego źródła danych, w pliku `config/config.py` zmień ścieżkę na wskazującą katalog z plikami źródłowymi
- uruchom plik:
  - `production_processor/application.py` – aby przeprowadzić symulację procesu decyzyjnego gracza
  - `manual_word_modification/word_modification.py` – aby tworzyć lub modyfikować świat
- obrazy generowane przez aplikację znajdziesz w katalogu `gameplays`

### Uwagi MAC

Przy instalacji pakietu `pygraphviz` może pojawić się błąd budowania biblioteki `graphviz`, który można rozwiązać poprzez:

```bash
PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.8.12
pip install --global-option=build_ext --global-option="-I/opt/homebrew/include/" --global-option="-L/opt/homebrew/lib/graphviz" pygraphviz==1.7
```

Efekty graficzne działania skryptów pojawiają się w katalogach wskazanych w poszczególnych skryptach. Jest to albo 
katalog ze światami w katalogu źródłowym albo podkatalogi katalogu z repozytorium.

## Dostępne skrypty
- `api_examples`, `api_json_validation`, `api_visualise_production`
  - Azure Function do udostępniania schemat pliku `.json` poprzez RestAPI
  - Azure Function do walidowania plików produkcji i świata poprzez RestAPI
  - Azure Function do generowania schematów produkcji poprzez RestAPI
- `json_validation`
  - `json_validate`: do walidowania plików plików produkcji i świata lokalnie
- `manual_world_modifications`
  - `world_modifications`: do ręcznego modyfikowania wskazanego pliku świata przez projektanta
- `production_hierarchy` (pomocnicze)
  -  `visualise_production_hierarchy`: wizualizacja hierarchii produkcji (domyślnie w pliku w katalogu `visualisation/out_production_hierarchy_tree`)
- `production_match` (pomocnicze)
  - `find_productions_to_perform`: znajduje i wypisuje listę produkcji pasującą do wskazanego na początku skryptu świata. 
Szczegóły dopasowań wizualizuje w katalogu `production_match/out`
- `production_processor`
  - `application`: Przeprowadza użytkownika przez proces decyzyjny gry zaczynając od stanu startowego wskazanego na 
początku skryptu świata. Znajduje dopasowania produkcji z plików misji wskazanych na początku skryptu, wykonuje wybraną 
przez użytkownika produkcję w wybranym wariancie dopasowania i od nowa znajduje dopasowania produkcji do zmienionego 
świata dopóki użytkownik nie przerwie cyklu. Zapisuje wizualizacje kolejnych stanów świata i warianty dopasowań 
w podkatalogu katalogu `gameplays`. Pozwala na zapisanie tamże aktualnego stanu świata w pliku `.json`.


