"""Classify directors by community of origin, from their printed names.

Why this is a four-way scheme and not a binary
----------------------------------------------
Interwar Egyptian boards were not divided between Europeans and Egyptians. A
third bloc — the *mutamassirun*, Egyptianised minorities: Sephardi and
Egyptian Jews, Greeks, Armenians, Syro-Lebanese Christians — supplied a large
share of directors and is the group most of the historiography is actually
about (Cattaui, Mosseri, Benachi, Choremi, Sursock, Matossian). Folding them
into "European" would attribute their positions to foreign capital; folding
them into "Egyptian" would erase the distinction the period turned on. They
are therefore their own category, and the European/Arab contrast is estimated
with them held separate.

How the inference works
-----------------------
Names are all the source gives, so origin is *imputed*, not observed. Two
signals, in priority order:

1. **Surname**, via explicit lexicons and orthographic patterns (Armenian
   ``-ian``, Greek ``-akis``/``-poulos``/``-achi``). Surnames carry community
   in this setting; given names do not, because the minority bourgeoisie
   used French given names — Joseph Cattaui and Joseph Aslan were not French.
2. **Arabic given names and name particles** (``Mohamed``, ``Abdel``,
   ``Abou``, ``El-``), which are close to unambiguous here and give the Arab
   Egyptian category its recall.

Anything unmatched stays ``unknown`` rather than being guessed into a
category. Every classification records which rule fired, so the coding can be
audited and corrected — see ``origin_report``.

**This is imputation with error.** Treat the categories as a measured variable
with misclassification, not as ground truth, and read
``docs/ORIGIN_CODING.md`` before using them in an argument.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from unidecode import unidecode

ARAB = "arab_egyptian"
EUROPEAN = "european"
MINORITY = "local_minority"
UNKNOWN = "unknown"

# --- Arabic given names and particles ----------------------------------------
ARABIC_GIVEN = {
    "mohamed", "mohammed", "muhammad", "mahmoud", "mahmud", "ahmed", "ahmad",
    "hassan", "hasan", "hussein", "hussain", "husein", "ali", "aly", "ibrahim",
    "moustapha", "mustapha", "mostafa", "moustafa", "omar", "osman", "othman",
    "youssef", "yussouf", "yousef", "yusuf", "kamel", "kamal", "fouad", "fuad",
    "sayed", "sayyed", "said", "saïd", "saleh", "salah", "sami", "samy",
    "abdallah", "abdalla", "abdel", "abd", "abdul", "abdo", "aziz", "rahman",
    "rahim", "hamid", "hamed", "hamdi", "sabry", "sabri", "fahmy", "fahmi",
    "zaki", "zaky", "sidky", "sidki", "sirry", "serry", "chafik", "chafic",
    "shafik", "tewfik", "tawfik", "taufik", "riad", "riyad", "rachid",
    "rashid", "nagib", "naguib", "amin", "amine", "anwar", "ismail", "ismaïl",
    "khalil", "hafez", "hafiz", "farid", "fariد", "galal", "gamal", "gamil",
    "hamza", "idris", "kadri", "kadry", "lotfi", "loutfi", "mahfouz",
    "mansour", "marei", "mazloum", "mokhtar", "morsi", "nashaat", "nazmi",
    "nour", "raafat", "ragheb", "ratib", "sadek", "sadik", "salem", "chawki",
    "chaoui", "sherif", "cherif", "soliman", "suleiman", "wahba", "yehia",
    "yahia", "zohdy", "zohdi", "zulficar", "zulfikar", "badawi", "badaoui",
    "bahgat", "bakri", "barakat", "dessouki", "eldin", "dine", "ezzat",
    "fathi", "fahmi", "fikri", "fikry", "gaafar", "gafar", "hilmi", "helmi",
    "khairi", "khairy", "labib", "maher", "mounir", "mustafa", "nabil",
    "nadim", "rifaat", "rushdi", "roushdy", "safwat", "sami", "shukri",
    "chukri", "wahid", "wassef", "yakan", "zeinab", "fatma", "aicha",
}
ARABIC_PARTICLE = re.compile(
    r"(?:^|\s)(?:abdel|abdul|abd|abou|abu|aboul|abul|el|al|ibn|bin|ben)\b|"
    r"\bel[- ]|\bal[- ]|(?:^|\s)ez\s?el|(?:^|\s)nour\s?el", re.I)
ARABIC_SURNAME = {
    "abaza", "abboud", "aboud", "attia", "azmi", "badrawi", "barakat",
    "chohayeb", "dessouki", "diab", "farghali", "fawzi", "gabr", "ghali",
    "haggag", "hamza", "harb", "hassanein", "kamel", "khachaba", "khashaba",
    "marei", "mazloum", "nahas", "nashed", "okasha", "rateb", "ratib",
    "riaz", "sadek", "sakr", "salem", "sallam", "sarwat", "serageldin",
    "shawarby", "sherei", "sidky", "sirry", "soliman", "tawil", "wahba",
    "wissa", "yakan", "yehia", "zaghloul", "zaki", "zulficar", "mahrous",
    "shukri", "chohaib", "seif", "attal", "elwi", "eloui", "kholi", "kholy",
}

# --- Egyptianised minorities --------------------------------------------------
JEWISH = {
    "cattaui", "cattaoui", "qattawi", "mosseri", "menasce", "suares", "suarès",
    "adda", "cicurel", "aghion", "harari", "rolo", "curiel", "pinto", "tilche",
    "smouha", "ades", "douek", "castro", "sasson", "nahman", "picciotto",
    "nahmias", "cohen", "levy", "levi", "hazan", "alfassa", "barcilon",
    "ezri", "lebovich", "mizrahi", "mizrachi", "setton", "sornaga", "romano",
    "bigio", "hakim", "hayim", "haim", "mercado", "modiano", "naggar",
    "politi", "sasoon", "tawil", "toriel", "zilkha", "abravanel", "aslan",
    "benin", "carasso", "chalom", "danon", "eskenazi", "farhi", "franco",
    "galante", "goar", "grunberg", "hasson", "israel", "kohn", "lagnado",
    "mann", "matalon", "menache", "nadler", "nissim", "palacci", "peres",
    "rossano", "salama", "sanua", "schemla", "sedaka", "tarrab", "tobi",
    "weinstein", "yedid", "goradesky", "silvera", "vitali",
}
GREEK = {
    "benachi", "choremi", "salvago", "zervudachi", "sinadino", "casulli",
    "rodocanachi", "cozzika", "averoff", "pilavachi", "zarifi", "mitarachi",
    "sakellaridis", "spetseropoulo", "dimopoulo", "eliasco", "psaltoff",
    "tsakiroglou", "valsamachi", "xenakis", "ralli", "petrocochino",
    "stavrides", "theodorakis", "papadakis", "cavafy", "cavafis", "anastasi",
    "argyropoulo", "calvocoressi", "carvalho", "cassavetti", "coussoulis",
    "danaos", "embiricos", "galanis", "georgiadis", "gonatas", "hadjikyriakos",
    "kyriazi", "lagoudakis", "michalinos", "negroponte", "nomicos",
    "pangalos", "papayanni", "paraskevas", "petridis", "polites", "scaramanga",
    "sofianopoulo", "stefanidis", "vagliano", "vlasto", "zaimis", "zannis",
}
ARMENIAN_SUFFIX = re.compile(r"(?:ian|yan|jian|gian|djian|kian|osian)$", re.I)
ARMENIAN = {
    "matossian", "nubar", "gulbenkian", "tanielian", "yeghiayan", "abro",
    "arakelian", "bogossian", "chakerian", "hagopian", "kevorkian",
    "manoukian", "melkonian", "mouradian", "ohanian", "papazian",
    "sarkissian", "tchakerian", "vartanian", "zakarian",
}
LEVANTINE = {
    "sursock", "arcache", "awad", "ghandour", "takla", "sednaoui", "chalhoub",
    "debbane", "zananiri", "khoury", "khouri", "sabbagh", "bittar", "chiha",
    "eid", "elias", "farah", "gargour", "hanna", "haddad", "jabre", "kahil",
    "karam", "kfoury", "malouf", "mattar", "nahas", "rizk", "saad", "safar",
    "sayegh", "chedid", "shedid", "sabet", "tagher", "tueni", "yared",
    "zaccour", "zogheb", "aboussouan", "bahri", "boulad", "chammas",
    "corm", "dabbas", "fattal", "gemayel", "homsy", "kettaneh", "lahoud",
    "nammour", "sioufi", "tabet", "tabbagh", "trad", "zalzal",
}
GREEK_SUFFIX = re.compile(r"(?:akis|opoulos|opoulo|poulos|idis|iadis|achi|"
                          r"oglou|aki|atos)$", re.I)

# --- Europeans ----------------------------------------------------------------
BRITISH = {
    "barker", "carver", "lowe", "finney", "hopkinson", "bate", "clavell",
    "alexander", "smith", "brown", "jones", "wilson", "taylor", "davies",
    "harris", "clark", "walker", "young", "king", "wright", "baker", "hill",
    "green", "adams", "campbell", "mitchell", "roberts", "turner", "phillips",
    "parker", "evans", "edwards", "collins", "stewart", "morris", "murphy",
    "cook", "rogers", "morgan", "bell", "bailey", "reed", "kelly", "howard",
    "ward", "cox", "richardson", "wood", "watson", "brooks", "gray",
    "james", "price", "bennett", "barnes", "ross", "henderson", "coles",
    "graham", "wallace", "hamilton", "ferguson", "grant", "mcpherson",
    "macpherson", "russell", "thomson", "thompson", "webster", "whittall",
    "peel", "acland", "brereton", "docker", "goschen", "hornby", "keown",
    "lindsay", "maclean", "moseley", "pilcher", "ramsay", "strachan",
    "sutherland", "tottenham", "vincent", "webb", "wheeler", "willcocks",
    "abdy", "perrott", "barran", "cheetham", "loraine", "lampson",
}
FRENCH_BELGIAN_SWISS = {
    "allard", "delsemme", "epaulard", "monnerat", "pollet", "thiriez",
    "landerer", "gasche", "baehler", "boye", "boyé", "vincenot", "fumaroli",
    "naus", "dupont", "durand", "lefebvre", "moreau", "laurent", "simon",
    "michel", "leroy", "roux", "david", "bertrand", "morel", "fournier",
    "girard", "bonnet", "dupuis", "lambert", "fontaine", "rousseau",
    "vincent", "muller", "faure", "andre", "mercier", "blanc", "guerin",
    "boyer", "garnier", "chevalier", "francois", "legrand", "gauthier",
    "garcia", "perrin", "robin", "clement", "morin", "nicolas", "henry",
    "roussel", "mathieu", "gautier", "masson", "marchand", "duval", "denis",
    "dumont", "marie", "lemaire", "noel", "meyer", "dufour", "meunier",
    "brun", "blanchard", "giraud", "joly", "riviere", "lucas", "brunet",
    "gaillard", "barbier", "arnaud", "martinez", "gerard", "roche", "renard",
    "schmitt", "roy", "leroux", "colin", "vidal", "caron", "picard",
    "roger", "fabre", "aubert", "lefevre", "bourgeois", "renaud", "olivier",
    "philippe", "bourdon", "sauvage", "carre", "charpentier", "menard",
    "maillard", "baron", "bertin", "bailly", "herve", "schneider", "collet",
    "leger", "bouvier", "julien", "prevost", "millet", "perrot", "daniel",
    "cousin", "germain", "breton", "besson", "hubert", "blanchet", "jacquet",
    "chevallier", "legros", "renault", "carlier", "brunel", "lacroix",
    "humbert", "cordier", "pichon", "lemoine", "poulain", "pons", "cornet",
    "pelletier", "delaunay", "guillot", "chauvin", "aubry", "bousquet",
    "verdier", "rey", "berger", "dubois", "petit", "durant", "leblanc",
    "vidal", "salomon", "pasteur", "jacob", "peltier", "reynaud", "tissot",
    "borel", "favre", "perret", "bovet", "dubuis", "pittet", "rochat",
}
ITALIAN = {
    "malatesta", "pace", "grasso", "rossi", "russo", "ferrari", "esposito",
    "bianchi", "romano", "colombo", "ricci", "marino", "greco", "bruno",
    "gallo", "conti", "de luca", "mancini", "costa", "giordano", "rizzo",
    "lombardi", "moretti", "barbieri", "fontana", "santoro", "mariani",
    "rinaldi", "caruso", "ferrara", "galli", "martini", "leone", "longo",
    "gentile", "martinelli", "vitale", "lombardo", "serra", "coppola",
    "de santis", "marchetti", "parisi", "villa", "conte", "ferraro",
    "ferri", "fabbri", "bianco", "marini", "grossi", "cattaneo", "morelli",
    "amato", "silvestri", "mazza", "testa", "grassi", "pellegrini",
    "carbone", "giuliani", "benedetti", "barone", "rossetti", "caputo",
    "montanari", "guerra", "palumbo", "sanna", "farina", "rizzi", "monti",
    "cattani", "cantoni", "sciuto", "arato", "dentamaro", "vitali",
    "riquez", "cavalieri", "franchi", "levi", "orlando", "sabatini",
}
OTHER_EUROPEAN = {
    "muller", "schmidt", "schneider", "fischer", "weber", "wagner", "becker",
    "hoffmann", "schulz", "koch", "richter", "klein", "wolf", "neumann",
    "schwarz", "zimmermann", "braun", "krueger", "hofmann", "hartmann",
    "lange", "werner", "krause", "meier", "lehmann", "koehler", "herrmann",
    "walter", "kaiser", "peters", "moeller", "berg", "nilsson", "andersson",
    "olsen", "hansen", "jensen", "larsen", "petersen", "vandenberg",
    "vanderbilt", "van der", "de vries", "bakker", "visser", "smit",
    "meijer", "mulder", "bos", "vos", "peeters", "janssens", "maes",
    "willems", "claes", "goossens", "wouters", "declercq", "coppens",
    "martz", "ernst", "hoffman", "steiner", "keller", "brandt", "engel",
}


# Names harvested from this corpus's own long tail, coded by hand. Without
# them recall stalls: the lexicons above cover the famous families, while most
# directors are ordinary men who appear two or three times.
BRITISH |= {
    "murray", "burgoyne", "wild", "singleton", "mackay", "mackenzie", "irwin",
    "dukes", "mills", "davis", "barron", "malone", "nichols", "saxby",
    "horne", "grieve", "williams", "delany", "buxton", "hargreaves",
    "critchley", "richmond", "flower", "awre", "rye", "nathan", "martin",
    "dawson", "gibson", "hunter", "lawson", "marshall", "newton", "osborne",
    "palmer", "pearson", "sanders", "sharp", "shaw", "stanley", "sinclair",
    "stone", "wells", "west", "wilkinson", "wyatt", "child", "cooper",
    "crawford", "duncan", "fraser", "gordon", "harvey", "holt", "hughes",
    "jackson", "johnston", "lloyd", "mason", "miller", "moore", "murray",
    "nelson", "norman", "page", "patterson", "porter", "reid", "scott",
    "spencer", "watts", "white", "wynne", "gray", "greaves",
}
FRENCH_BELGIAN_SWISS |= {
    "lefrere", "riches", "mullet", "minost", "savon", "begue", "bonafous",
    "laherrere", "ithier", "raybaud", "vallet", "autrand", "grimprel",
    "vincendon", "pottier", "vaucher", "goulene", "boels", "hauman",
    "neuflize", "destree", "rolin", "empain", "jacobs", "trembley",
    "vandamme", "van damme", "lambiotte", "ramlot", "feyerick", "leten",
    "boissonas", "raemy", "jacot", "descombes", "allemann", "burckhardt",
    "luchsinger", "wyler", "pupikofer", "hahnloser", "kupper", "groppi",
    "reinhart", "halter", "bauerle", "muntz", "lindemann", "behrend",
    "wedemeyer", "jensens", "appel", "delaporte", "gaillard", "thevenin",
    "dumas", "berthier", "chapuis", "cornu", "ducret", "favez", "golay",
    "grandjean", "guillaume", "jaquet", "monod", "naville", "odier",
    "pictet", "sandoz", "schwob", "vautier", "wenger", "zbinden",
}
ITALIAN |= {
    "pegna", "vannucci", "corsi", "vais", "sinigaglia", "spathis",
    "dentamaro", "belleni", "diacono", "lascaris",
}
JEWISH |= {
    "besso", "ismalun", "misrahi", "misrahy", "barda", "ambron", "toriel",
    "messiqua", "sachs", "lumbroso", "zaccai", "garboua", "dabbah",
    "strologo", "sekaly", "shama", "morpurgo", "alphandary", "nacamuli",
    "brakha", "zarmati", "antebi", "hemsi", "lisbona", "ambache",
    "ginsberg", "pathy", "polnauer", "lian", "adee", "benveniste",
    "bensimon", "beninson", "cohn", "dwek", "elmaleh", "fresco", "gubbay",
    "hazzan", "levi", "menasse", "mizrahi", "nahum", "nissim", "perahia",
    "sacerdoti", "saul", "schinasi", "sion", "tarica", "varon", "yahuda",
}
GREEK |= {
    "dellaporta", "mavro", "calomiris", "tsekis", "lagonico", "mouratiadi",
    "christomanos", "pezas", "athenogenes", "vraila", "matsa", "moraitinis",
    "stephanou", "christou", "goulandris", "sakellarios", "pappas",
}
LEVANTINE |= {
    "rabbath", "toutounji", "lebnan", "schemeil", "bustros", "sarofim",
    "doss", "wahib", "khayatt", "bishara", "wissa", "ghali", "shenouda",
    "riad", "sidarouss", "fanous", "guirguis", "mikhail", "morcos",
    "tadros", "yacoub", "zaki", "bahgouri", "andraos", "atalla",
}
ARABIC_SURNAME |= {
    "afifi", "atta", "mahran", "farghaly", "issawi", "rached", "halim",
    "wakil", "zayed", "izzet", "abdullah", "zakaria", "shalaby",
}

# Not people. These are decorations, offices, places and industries that the
# roster prints alongside names and the parser occasionally captures as an
# entry. They are excluded before any analysis rather than coded, since an
# honour is not a director.
_NOT_A_PERSON = re.compile(
    r"(?i)\b(comit[eé]|commission|gouvernemental|couronne|officier|"
    r"chevalier|commandeur|l[eé]gion|croix\s+de\s+guerre|m[eé]rite|"
    r"ancien\s+ministre|d[eé]put[eé]|s[eé]nateur|universit|oxford|"
    r"cambridge|college|[eé]tudes|dipl[oô]m|licenci[eé]|docteur\s+en|"
    r"industr|soierie|tuyaux|ciment|portland|linen|cotton\s+co|"
    r"le\s+caire|alexandrie|egypte?\b|egyptiennes?\b|belgique|paris|"
    r"londres|artistes|banque|soci[eé]t[eé]|compagnie|etablissements|"
    r"caire\b|alexandrie\b|"
    r"[eé]tablissements|distiller|fabrique|usines?|maison\s|agence)\b")


def is_person(name: str) -> bool:
    """Is this record a human being at all?

    The roster interleaves names with honours, offices and qualifications, and
    the parser sometimes takes one of those for an entry. The test is where the
    honour sits, not whether it is present: a record that *opens* with one is
    not a director, while one that opens with a name and carries an honour
    after it — "Baehler Charles Commandeur Medjidié", "Abdel Haï Khalil Bey
    Député" — is a director described in full.

    Matching the vocabulary anywhere in the string, as an earlier version did,
    discarded 76 real directorships including several of the best-connected
    men in the dataset.

    Three classes of record are rejected wherever their marker sits, because
    no printed name in this source contains them: an academic institution, a
    company suffix, and a degree read alongside a university.
    """
    text = unidecode(str(name)).strip()
    letters = re.sub(r"[^A-Za-z]", "", text)
    if len(letters) < 4:
        return False
    # Qualifications and institutions are never part of a name here, wherever
    # they sit: "St. John's College Oxford" is a line from a biography.
    if re.search(r"(?i)\b(?:college|universit|oxford|cambridge)\b", text):
        return False
    # Nor is a company suffix: "Upper Egypt Oinning-Co" is a firm.
    if re.search(r"(?i)[\s-](?:co|ltd|cie|s\.?\s?a\.?\s?e)\.?$", text):
        return False
    head = text
    for _ in range(3):
        stripped = re.sub(r"(?i)^(?:the|le|la|les|l'|el|grande?|premier|haut|"
                          r"sous|vice|son|s\.\s?e\.|s\.\s?a\.)\s+", "", head)
        if stripped == head:
            break
        head = stripped
    return not _NOT_A_PERSON.match(head)


# Coptic and Levantine surnames that carry French given names and would
# otherwise fall through to the European lexicons. Names both communities use
# — Khalil, Soliman, Zaki, Riad — are deliberately excluded: Mohamed Mahmoud
# Khalil was a Muslim Egyptian, and a shared name is evidence either way.
LEVANTINE |= {
    "bassili", "basili", "bicharat", "boutros", "hanna", "iskandar",
    "makarios", "nakhla", "sarkis", "shenouda", "takla",
}
LEVANTINE -= {"khalil", "soliman", "zaki", "riad", "gabriel"}


# European given names. These must never, on their own, make someone European:
# the Egyptianised minorities used them universally, so matching on them would
# quietly recode Copts, Levantines and Greeks as foreigners — biasing the very
# comparison the categories exist to draw. Any European classification must
# rest on a token outside this set.
EUROPEAN_GIVEN = {
    "joseph", "georges", "george", "albert", "charles", "jean", "maurice",
    "robert", "jacques", "victor", "leon", "leonidas", "henry", "henri",
    "andre", "john", "pierre", "edouard", "edward", "emile", "louis", "paul",
    "max", "nicolas", "nicolo", "rene", "alfred", "constantin", "alexandre",
    "alexander", "william", "raymond", "antoine", "marcel", "fernand",
    "michel", "david", "simon", "daniel", "julien", "philippe", "denis",
    "germain", "hubert", "olivier", "salomon", "jacob", "james", "roger",
    "martin", "vincent", "marie", "gaston", "lucien", "ernest", "gustave",
    "eugene", "camille", "felix", "arthur", "frederic", "frederick", "hector",
    "achille", "adolphe", "alexis", "anatole", "armand", "aristide", "auguste",
    "benjamin", "bernard", "bruno", "cesar", "christian", "claude", "clement",
    "edgard", "edmond", "elie", "etienne", "eduard", "francois", "frank",
    "gabriel", "gerard", "gilbert", "guillaume", "gustav", "isaac", "jules",
    "leopold", "lionel", "marc", "mario", "michael", "moise", "nissim",
    "oscar", "peter", "raphael", "richard", "rodolphe", "samuel", "stephane",
    "sylvain", "theodore", "thomas", "tristan", "valentin", "walter", "xavier",
}
# Purge given names that had been sitting in the surname lexicons.
for _s in (BRITISH, FRENCH_BELGIAN_SWISS, ITALIAN, OTHER_EUROPEAN):
    _s -= EUROPEAN_GIVEN


@dataclass(frozen=True)
class Origin:
    group: str
    subgroup: str
    rule: str          # which signal fired, so a coding can be audited


def _tokens(name: str) -> list[str]:
    flat = unidecode(str(name)).lower()
    flat = re.sub(r"[^a-z\s'-]", " ", flat)
    return [t for t in re.split(r"[\s'-]+", flat) if len(t) > 1]


# Words that are titles or honorifics, never evidence of origin. 'Bey' and
# 'Pacha' in particular were held across every community here.
_TITLES = {"bey", "beik", "pacha", "pasha", "effendi", "eff", "sir", "lord",
           "dr", "mtre", "me", "ing", "comm", "cav", "uff", "prof", "baron",
           "comte", "cheikh", "sheikh", "hon", "col", "gen", "capt", "rev",
           "madame", "mme", "mlle", "prince", "princesse", "son", "altesse"}


def classify(name: str) -> Origin:
    """Impute one director's community of origin from their printed name."""
    toks = [t for t in _tokens(name) if t not in _TITLES]
    if not toks:
        return Origin(UNKNOWN, "", "empty")
    joined = " ".join(toks)

    # 1. Surname lexicons and orthography. Checked over every token, because
    #    the volumes invert name order between editions.
    for tok in toks:
        if tok in JEWISH:
            return Origin(MINORITY, "jewish", f"surname:{tok}")
        if tok in GREEK or (GREEK_SUFFIX.search(tok) and len(tok) > 6):
            return Origin(MINORITY, "greek", f"surname:{tok}")
        if tok in ARMENIAN or (ARMENIAN_SUFFIX.search(tok) and len(tok) > 6):
            return Origin(MINORITY, "armenian", f"surname:{tok}")
        if tok in LEVANTINE:
            return Origin(MINORITY, "levantine", f"surname:{tok}")

    for tok in toks:
        if tok in EUROPEAN_GIVEN:
            continue   # a given name is not evidence of a European surname
        if tok in BRITISH:
            return Origin(EUROPEAN, "british", f"surname:{tok}")
        if tok in FRENCH_BELGIAN_SWISS:
            return Origin(EUROPEAN, "french_belgian_swiss", f"surname:{tok}")
        if tok in ITALIAN:
            return Origin(EUROPEAN, "italian", f"surname:{tok}")
        if tok in OTHER_EUROPEAN:
            return Origin(EUROPEAN, "other_european", f"surname:{tok}")

    # 2. Arabic given names and particles.
    if ARABIC_PARTICLE.search(joined):
        return Origin(ARAB, "muslim_egyptian", "particle")
    for tok in toks:
        if tok in ARABIC_SURNAME:
            return Origin(ARAB, "muslim_egyptian", f"surname:{tok}")
    for tok in toks:
        if tok in ARABIC_GIVEN:
            return Origin(ARAB, "muslim_egyptian", f"given:{tok}")

    return Origin(UNKNOWN, "", "unmatched")


def classify_frame(labels) -> "pd.DataFrame":
    import pandas as pd

    rows = [classify(x) for x in labels]
    return pd.DataFrame({
        "label": list(labels),
        "origin": [r.group for r in rows],
        "origin_detail": [r.subgroup for r in rows],
        "origin_rule": [r.rule for r in rows],
    })


def origin_report(labels) -> "pd.DataFrame":
    """Coverage by category, for judging how far the coding can be pushed."""
    import pandas as pd

    df = classify_frame(labels)
    out = (df.groupby("origin").size().rename("n").reset_index()
             .assign(share=lambda d: d.n / d.n.sum()))
    return out.sort_values("n", ascending=False)
