"""
Enum classes for normalized property listing data.

These enums provide standardized values across all real estate sites,
enabling consistent data format and duplicate detection.
"""

from enum import Enum

__all__ = [
    "City",
    "Currency",
    "OfferType",
    "PlovdivNeighborhood",
    "PropertyType",
    "SofiaNeighborhood",
]


class OfferType(str, Enum):
    """Type of property offer."""

    SALE = "продава"
    RENT = "наем"


class PropertyType(str, Enum):
    """Type of property."""

    STUDIO = "студио"
    ONE_ROOM = "едностаен"
    TWO_ROOM = "двустаен"
    THREE_ROOM = "тристаен"
    FOUR_ROOM = "четиристаен"
    MULTI_ROOM = "многостаен"
    MAISONETTE = "мезонет"
    LAND = "земя"
    HOUSE = "къща"
    OFFICE = "офис"
    STUDIO_APARTMENT = "ателие"
    GARAGE = "гараж"
    PARKING = "паркомясто"


class City(str, Enum):
    """Major Bulgarian cities."""

    SOFIA = "София"
    PLOVDIV = "Пловдив"
    VARNA = "Варна"
    BURGAS = "Бургас"


class Currency(str, Enum):
    """Supported currencies."""

    EUR = "EUR"
    BGN = "BGN"


class SofiaNeighborhood(str, Enum):
    """Sofia neighborhoods."""

    LOZENETS = "Лозенец"
    CENTER = "Център"
    IVAN_VAZOV = "Иван Вазов"
    OBORISHTE = "Оборище"
    DIANABAD = "Дианабад"
    IZTOK = "Изток"
    IZGREV = "Изгрев"
    YAVOROV = "Яворов"
    BOROVO = "Борово"
    GOTSE_DELCHEV = "Гоце Делчев"
    STRELBISHTE = "Стрелбище"
    HIPODRUMA = "Хиподрума"
    HLADILNIKA = "Хладилника"
    BELITE_BREZI = "Белите брези"
    VITOSHA = "Витоша"
    MANASTIRSKI_LIVADI = "Манастирски ливади"
    STUDENTSKI_GRAD = "Студентски град"
    MLADOST = "Младост"
    MLADOST_1 = "Младост 1"
    MLADOST_2 = "Младост 2"
    MLADOST_3 = "Младост 3"
    MLADOST_4 = "Младост 4"
    DRUZHBA = "Дружба"
    DRUZHBA_1 = "Дружба 1"
    DRUZHBA_2 = "Дружба 2"
    LYULIN = "Люлин"
    NADEZHDA = "Надежда"
    SLATINA = "Слатина"
    GEO_MILEV = "Гео Милев"
    REDUTA = "Редута"
    PODUYANE = "Подуяне"
    KRASTOVA_VADA = "Кръстова вада"
    MALINOVA_DOLINA = "Малинова долина"
    DRAGALEVTSI = "Драгалевци"
    BOYANA = "Бояна"
    SIMEONOVO = "Симеоново"
    KNYAZHEVO = "Княжево"
    OVCHA_KUPEL = "Овча купел"
    KRASNO_SELO = "Красно село"
    LAGERA = "Лагера"
    BUKSTON = "Бъкстон"
    PAVLOVO = "Павлово"
    HADJI_DIMITAR = "Хаджи Димитър"
    LEVSKI = "Левски"
    LEVSKI_G = "Левски Г"
    LEVSKI_V = "Левски В"
    SUHA_REKA = "Сухата река"
    BANISHORA = "Банишора"
    DOKTORSKI_PAMETNIK = "Докторски паметник"
    DARVENITSA = "Дървеница"
    MUSAGENITSA = "Мусагеница"
    MEDITSINSKA_AKADEMIYA = "Медицинска академия"
    BORISOVA_GRADINA = "Борисова градина"
    KRIVA_REKA = "Крива река"
    MODERNO_PREDGRADIE = "Модерно предградие"
    ZONA_B5 = "Зона Б-5"
    ZONA_B18 = "Зона Б-18"
    ZONA_B19 = "Зона Б-19"
    SVETA_TROITSA = "Света Троица"
    SERDIKA = "Сердика"
    TRIAGALNIKA = "Триъгълника"
    POLIGONA = "Полигона"
    MOTOPISTA = "Мотописта"
    SVOBODA = "Свобода"
    NADEZHDA_1 = "Надежда 1"
    NADEZHDA_2 = "Надежда 2"
    NADEZHDA_3 = "Надежда 3"
    NADEZHDA_4 = "Надежда 4"
    TOLSTOY = "Толстой"
    FONDOVI_ZHILISHTA = "Фондови жилища"
    ZAPADEN_PARK = "Западен парк"
    RAZSADNIKA = "Разсадника"
    BELI_BREZI = "Бели брези"
    KARPUZITSA = "Карпузица"
    ILINDEN = "Илинден"
    BENKOVSKI = "Бенковски"
    ORLANDOVTSI = "Орландовци"
    MALASHEVTSI = "Малашевци"
    HRISTO_SMIRNENSKI = "Христо Смирненски"
    GORNA_BANYA = "Горна баня"
    BANKYA = "Банкя"
    ILIENTSI = "Илиянци"
    VRAZHDEBNA = "Враждебна"
    BOTUNETS = "Ботунец"
    PANCHAREVO = "Панчарево"
    BISTRITSA = "Бистрица"
    GERMANA = "Германа"


class PlovdivNeighborhood(str, Enum):
    """Plovdiv neighborhoods."""

    CENTER = "Център"
    KAMENITSA_1 = "Каменица 1"
    KAMENITSA_2 = "Каменица 2"
    MARASHA = "Мараша"
    MLADEJKI_HALM = "Младежки хълм"
    KARSHIYAKA = "Кършияка"
    TRAKIA = "Тракия"
    SMIRNENSKI = "Смирненски"
    GREBNA_BAZA = "Гребна база"
    VASTANICHESKI = "Въстанически"
    HRISTO_BOTEV = "Христо Ботев"
    YUZHEN = "Южен"
    KYUCHUK_PARIJ = "Кючук Париж"
    GAGARIN = "Гагарин"
    IZGREV = "Изгрев"
    ZAHARNA_FABRIKA = "Захарна фабрика"
    TSENTRALNA_GARA = "Централна гара"
    BELOMORSKI = "Беломорски"
    VMI = "ВМИ"
    PESHTERSKO_SHOSE = "Пещерско шосе"
    OTDIH_I_KULTURA = "Отдих и Култура"
    ROGOSHKO_SHOSE = "Рогошко шосе"
    BUNARDZHIKA = "Бунарджика"
    KARLOVSKO_SHOSE = "Карловско шосе"
    TODOR_KABLESHKOV = "Тодор Каблешков"
    TSAR_SIMEON = "Цар Симеон"
    INDUSTRIALNA_ZONA = "Индустриална зона"
    BATAK = "Батак"
    PLOVDIVSKI_UNIVERSITET = "Пловдивски университет"
    SADIYSKI = "Съдийски"
    KAPANA = "Капана"
    FILIPOVO = "Филипово"
    PROSLAV = "Прослав"
    KOMATEVO = "Коматево"
    OSTROMILA = "Остромила"
    STOLIPINOVO = "Столипиново"
    HRISTO_SMIRNENSKI = "Христо Смирненски"
    KYSHLA = "Кършала"
