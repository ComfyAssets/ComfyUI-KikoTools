"""Option tables for the Character Hint nodes.

Every table maps the label shown in the node to the phrase written into the
hint. The phrases were checked against MiniMax H3 Image: an option is listed
only when the model draws it. ``UNSET`` is the first choice of every field.
"""

from typing import Dict, Tuple

UNSET = "-"

Table = Dict[str, str]

MIN_AGE = 18
MAX_AGE = 90
DEFAULT_AGE = 25

HERITAGE: Tuple[str, ...] = (
    "Afghan",
    "Albanian",
    "American",
    "Argentine",
    "Australian",
    "Austrian",
    "Belgian",
    "Brazilian",
    "British",
    "Bulgarian",
    "Canadian",
    "Chilean",
    "Chinese",
    "Colombian",
    "Croatian",
    "Cuban",
    "Czech",
    "Danish",
    "Dutch",
    "Egyptian",
    "Ethiopian",
    "Filipino",
    "Finnish",
    "French",
    "German",
    "Greek",
    "Hungarian",
    "Indian",
    "Indonesian",
    "Iranian",
    "Iraqi",
    "Irish",
    "Israeli",
    "Italian",
    "Japanese",
    "Jordanian",
    "Korean",
    "Lebanese",
    "Malaysian",
    "Mexican",
    "Moroccan",
    "Nigerian",
    "Norwegian",
    "Pakistani",
    "Peruvian",
    "Polish",
    "Portuguese",
    "Romanian",
    "Russian",
    "Saudi",
    "Scottish",
    "Serbian",
    "Singaporean",
    "South African",
    "Spanish",
    "Swedish",
    "Swiss",
    "Syrian",
    "Thai",
    "Turkish",
    "Ukrainian",
    "Venezuelan",
    "Vietnamese",
    "Welsh",
)

# --- Body -----------------------------------------------------------------

FEMALE_BODY: Table = {
    "Slim": "a slim build",
    "Muscular": "a muscular body",
    "Curvy": "a curvy body",
    "Voluptuous": "a voluptuous body",
    "Chubby": "a chubby body",
    "Heavyset": "a heavyset build",
    "Obese": "an obese body",
}

MALE_BODY: Table = {
    "Lean": "a lean body",
    "Ripped": "a ripped body",
    "Jacked": "a jacked body",
    "Powerlifter": "a powerlifter build",
    "Dad bod": "a dad bod",
    "Heavyset": "a husky, heavyset build",
}

BREAST_SIZE: Table = {
    "Small": "small breasts",
    "Large": "large breasts",
    "Very large": "very large breasts",
}

BUTT_SIZE: Table = {
    "Flat": "a flat butt",
    "Large": "a large butt",
    "Very large": "a very large butt",
}

# --- Face -----------------------------------------------------------------

FACE_SHAPE: Table = {
    "Round": "a round face",
    "Oblong": "an oblong face",
}

EYE_COLOR: Table = {
    "Dark brown": "dark brown eyes",
    "Light brown": "light brown eyes",
    "Hazel": "hazel eyes",
    "Amber": "amber eyes",
    "Green": "green eyes",
    "Blue": "blue eyes",
    "Grey": "grey eyes",
    "Violet": "violet eyes",
    "Turquoise": "turquoise eyes",
    "Silver": "silver eyes",
    "Red": "red eyes",
    "Pink": "pink eyes",
}

EYE_SHAPE: Table = {
    "Monolid": "monolid eyes",
    "Hooded": "hooded eyes",
    "Deep-set": "deep-set eyes",
}

EYE_DETAIL: Table = {
    "Defined eyelashes": "eyes framed by defined eyelashes",
    "Fine lines": "fine lines around the eyes",
    "Gold flecks": "flecks of gold in the iris",
    "Heterochromia": "heterochromia, one blue eye and one brown eye",
    "Bloodshot": "slightly reddened, bloodshot eyes",
}

NOSE: Table = {
    "Small": "a very small nose",
    "Button": "a button nose",
    "Very large": "a very large nose",
}

FEMALE_LIP_SHAPE: Table = {
    "Thin": "thin lips",
    "Full": "full lips",
    "Wide": "wide lips",
    "Cupid's bow": "cupid's bow lips",
}

MALE_LIP_SHAPE: Table = {
    "Thin": "thin lips",
    "Full": "full lips",
}

# The phrase is the colour only; the builder adds " lips".
LIP_COLOR: Table = {
    "Natural": "natural",
    "Nude pink": "nude-pink",
    "Peach": "peach",
    "Coral": "coral",
    "Pink": "pink",
    "Mauve": "mauve",
    "Berry": "berry",
    "Plum": "plum",
    "Red": "red",
    "Glossy red": "glossy red",
    "Burgundy": "burgundy",
    "Brown": "brown",
    "Black": "black",
}

# Each style is (look, lips). The hint reads "wearing <look>, and <lips>";
# a chosen lip colour replaces <lips>.
MAKEUP: Dict[str, Tuple[str, str]] = {
    "No makeup": ("no makeup, with natural skin texture", "bare lips"),
    "Natural": (
        "subtle natural makeup, sheer foundation, softly groomed brows, "
        "light mascara, peach blush",
        "nude-pink lips",
    ),
    "Dewy": (
        "dewy makeup, luminous hydrated-looking skin, subtle cream blush, "
        "softly highlighted cheekbones",
        "glossy nude lips",
    ),
    "Matte": (
        "matte makeup, an even shine-free complexion, softly sculpted "
        "cheeks, neutral eyeshadow",
        "matte nude lips",
    ),
    "Soft glam": (
        "soft glam makeup, smoothly blended taupe eyeshadow, softly defined "
        "eyeliner, fluttery lashes, warm blush",
        "satin nude lips",
    ),
    "Full glam": (
        "full glam makeup, sculpted cheekbones, shimmering eyeshadow, "
        "dramatic winged eyeliner, voluminous lashes",
        "precisely defined lipstick",
    ),
    "Gothic": (
        "gothic makeup, dark smokey eyeshadow, heavy black eyeliner, "
        "sharply defined brows",
        "deep burgundy lipstick",
    ),
    "1960s mod": (
        "1960s-inspired mod makeup, pale eyelids with a sharply defined "
        "dark crease, bold upper eyeliner, separated lower lashes",
        "pale pink lips",
    ),
    "1950s pin-up": (
        "classic 1950s pin-up makeup, crisp black winged eyeliner, softly "
        "shaded eyelids, arched brows, rosy cheeks",
        "vivid red lipstick",
    ),
    "Bohemian": (
        "bohemian-inspired makeup, softly blended earthy bronze eyeshadow, "
        "smudged brown eyeliner, sun-kissed blush",
        "warm nude lips",
    ),
    "Douyin": (
        "Douyin-inspired makeup, fine extended winged eyeliner, sparkling "
        "eyeshadow, defined spiky lashes, highlighted aegyo-sal fullness "
        "immediately beneath the lower lashes with a delicate contour below "
        "it, rosy blush",
        "glossy gradient lips",
    ),
    "Soft Korean": (
        "soft Korean-inspired makeup, luminous skin, straight softly "
        "defined brows, delicate brown eyeliner, subtle highlighted "
        "aegyo-sal immediately beneath the lower lashes, peach blush",
        "softly blurred gradient lips",
    ),
    "K-pop stage": (
        "K-pop stage-inspired makeup, precise winged eyeliner, shimmering "
        "eyelids, bright inner-eye highlights, separated lashes, sculpted "
        "blush",
        "vivid glossy lips",
    ),
    "Gyaru": (
        "Japanese gyaru-inspired makeup, dramatic eye-enlarging black "
        "eyeliner, extended outer eye corners, thick upper and lower false "
        "lashes, bright lower-eye highlights, sculpted nose contour",
        "glossy nude-pink lips",
    ),
    "Igari": (
        "Japanese igari-inspired makeup, translucent-looking skin, "
        "prominent rosy blush high on the cheeks beneath the eyes and "
        "across the bridge of the nose, minimal eyeliner",
        "softly tinted pink lips",
    ),
    "Smokey eye": (
        "classic smokey-eye makeup, charcoal eyeshadow smoothly blended "
        "around the upper and lower lash lines, black eyeliner, full lashes",
        "muted nude lips",
    ),
    "Bronzed": (
        "bronzed makeup, warm bronze eyeshadow, softly defined brown "
        "eyeliner, golden cheek highlights, warm terracotta blush",
        "caramel nude lips",
    ),
    "Soft romantic": (
        "soft romantic makeup, delicate pink eyeshadow, softly smudged "
        "brown eyeliner, fluttery lashes, rose blush",
        "satin rose-pink lips",
    ),
    "Monochromatic rose": (
        "monochromatic rose makeup, coordinated dusty-rose eyeshadow, rose " "blush",
        "rose lipstick with softly blended edges",
    ),
    "Peach": (
        "peach-toned makeup, soft apricot eyeshadow, peach blush, subtle "
        "brown mascara",
        "glossy peach lips",
    ),
    "Latte": (
        "latte-inspired makeup, layered tan and coffee-brown eyeshadow, "
        "softly smudged brown eyeliner, warm bronzer",
        "beige-brown lips",
    ),
    "1990s grunge": (
        "1990s-inspired grunge makeup, smudged black pencil eyeliner, muted "
        "brown eyeshadow, minimally blushed skin",
        "matte brownish-plum lips",
    ),
    "Punk": (
        "punk makeup, thick angular black eyeliner, bold saturated "
        "eyeshadow, roughly smudged lower lash lines",
        "dark matte lipstick",
    ),
    "Cat eye": (
        "cat-eye makeup, sharply pointed black eyeliner wings extending "
        "upward from the outer corners, neutral eyelids, defined lashes",
        "nude lips",
    ),
    "Siren eye": (
        "siren-eye makeup, elongated dark eyeliner with pointed inner "
        "corners and long lifted outer wings, softly smoked lash lines",
        "muted satin lips",
    ),
    "Puppy eye": (
        "puppy-eye makeup, thin brown eyeliner extending slightly downward "
        "at the outer corners, softly shaded lower lash lines, subtle blush",
        "pink tinted lips",
    ),
    "Cut crease": (
        "cut-crease makeup, a sharply defined dark eyeshadow crease above "
        "bright contrasting eyelids, crisp winged eyeliner, full lashes",
        "neutral lips",
    ),
    "Halo eye": (
        "halo-eye makeup, deep eyeshadow at the inner and outer eyelids "
        "with a bright shimmering center, softly defined lashes",
        "neutral lips",
    ),
    "Graphic liner": (
        "graphic editorial makeup, crisp geometric eyeliner extending above "
        "the eyelid crease, clean skin, minimal blush",
        "precisely defined neutral lips",
    ),
    "Colorful": (
        "colorful makeup, vivid blended pink, purple, and blue eyeshadow, "
        "defined black eyeliner, bright blush",
        "coordinated pink lips",
    ),
    "Pastel": (
        "pastel makeup, softly blended lavender and baby-blue eyeshadow, "
        "delicate eyeliner, pale pink blush",
        "soft pink lips",
    ),
    "Metallic": (
        "metallic makeup, reflective silver eyeshadow, crisp black "
        "eyeliner, cool cheek highlights",
        "satin mauve lips",
    ),
    "Glitter": (
        "glitter makeup, fine cosmetic glitter across the eyelids, "
        "sparkling inner corners, defined lashes, softly highlighted cheeks",
        "glossy lips",
    ),
    "Avant-garde editorial": (
        "avant-garde editorial makeup, asymmetrical blocks of saturated "
        "eyeshadow, unconventional eyeliner shapes, sculpted blush "
        "placement",
        "a sharply defined statement lip",
    ),
    "Festival": (
        "festival makeup, vivid shimmering eyeshadow, small decorative face "
        "gems around the outer eyes, luminous cheek highlights",
        "glossy pink lips",
    ),
    "Coquette": (
        "coquette-inspired makeup, soft pink eyelids, delicate winged "
        "eyeliner, fluttery lashes, rosy cheeks",
        "glossy rosebud-pink lips",
    ),
    "Vamp": (
        "vamp makeup, deep plum eyeshadow, elongated black eyeliner, subtly "
        "sculpted cheeks",
        "rich oxblood lipstick",
    ),
    "Classic red lip": (
        "classic red-lip makeup, an even natural-looking complexion, "
        "minimal neutral eyeshadow, delicate black eyeliner",
        "precisely outlined bold red lipstick",
    ),
    "Berry lip": (
        "berry-lip makeup, softly defined neutral eyes, subtle rose blush",
        "rich raspberry lipstick",
    ),
    "Glossy editorial": (
        "glossy editorial makeup, wet-look transparent shine on the "
        "eyelids, luminous cheekbones, softly groomed brows",
        "high-shine clear lip gloss",
    ),
}

FACIAL_HAIR: Table = {
    "Clean shaven": "a clean-shaven face",
    "Stubble": "stubble",
    "Goatee": "a goatee",
    "Van Dyke": "a Van Dyke beard",
    "Handlebar mustache": "a handlebar mustache",
    "Chevron mustache": "a chevron mustache",
    "Ducktail beard": "a ducktail beard",
    "Full beard": "a full beard",
}

EXPRESSION: Table = {
    "Neutral": "a neutral expression",
    "Happy": "a happy expression",
    "Smiling": "a smiling expression",
    "Grinning": "a grinning expression",
    "Laughing": "a laughing expression",
    "Amused": "an amused expression",
    "Playful": "a playful expression",
    "Mischievous": "a mischievous expression",
    "Smirking": "a smirking expression",
    "Smug": "a smug expression",
    "Proud": "a proud expression",
    "Shy": "a shy expression",
    "Loving": "a loving expression",
    "Flirtatious": "a flirtatious expression",
    "Surprised": "a surprised expression",
    "Shocked": "a shocked expression",
    "Confused": "a confused expression",
    "Nervous": "a nervous expression",
    "Worried": "a worried expression",
    "Fearful": "a fearful expression",
    "Bored": "a bored expression",
    "Skeptical": "a skeptical expression",
    "Suspicious": "a suspicious expression",
    "Frowning": "a frowning expression",
    "Scowling": "a scowling expression",
    "Angry": "an angry expression",
    "Frustrated": "a frustrated expression",
    "Disgusted": "a disgusted expression",
    "Contemptuous": "a contemptuous expression",
    "Fierce": "a fierce expression",
}

# --- Hair -----------------------------------------------------------------

HAIR_COLOR: Table = {
    "Black": "black hair",
    "Dark brown": "dark brown hair",
    "Chestnut": "chestnut hair",
    "Caramel brown": "caramel brown hair",
    "Mahogany": "mahogany hair",
    "Auburn": "auburn hair",
    "Copper": "copper hair",
    "Strawberry blonde": "strawberry blonde hair",
    "Honey blonde": "honey blonde hair",
    "Dirty blonde": "dirty blonde hair",
    "Ash blonde": "ash blonde hair",
    "Blonde": "blonde hair",
    "Platinum blonde": "platinum blonde hair",
    "Salt and pepper": "salt and pepper hair",
    "Silver": "silver hair",
    "White": "white hair",
    "Burgundy": "burgundy hair",
    "Pastel blue": "pastel blue hair",
    "Teal": "teal hair",
    "Emerald green": "emerald green hair",
    "Lavender": "lavender hair",
    "Hot pink": "hot pink hair",
    "Rose gold": "rose gold hair",
    "Peach": "peach hair",
    "Rainbow": "rainbow hair",
    "Ombre": "ombre hair",
    "Balayage": "balayage hair",
    "Highlights": "highlighted hair",
}

HAIR_LENGTH: Table = {
    "Buzzed": "buzzed hair",
    "Chin length": "chin length hair",
    "Shoulder length": "shoulder length hair",
    "Long": "long hair",
}

FEMALE_HAIR_STYLE: Table = {
    "Bob": "her hair in a bob cut",
    "French bob": "her hair in a French bob",
    "Long bob": "her hair in a long bob",
    "Curly bob": "her hair in a curly bob",
    "Pixie cut": "her hair in a pixie cut",
    "Shag cut": "her hair in a shag cut",
    "Undercut": "her hair in an undercut",
    "Mullet": "her hair in a mullet",
    "Asymmetrical cut": "her hair in an asymmetrical cut",
    "Afro": "an afro",
    "Cornrows": "cornrows",
    "Dreadlocks": "dreadlocks",
    "Box braids": "box braids",
    "Bantu knots": "bantu knots",
    "Halo braid": "a halo braid",
    "Single braid": "a fishtail braid",
    "Space buns": "her hair in space buns",
    "Top knot": "her hair in a top knot",
    "Messy bun": "her hair in a messy bun",
    "Low bun": "her hair in a low bun",
    "High ponytail": "her hair in a high ponytail",
    "Side ponytail": "her hair in a side ponytail",
    "Pigtails": "her hair in pigtails",
    "Half-up half-down": "her hair in a half-up half-down style",
    "Chignon": "her hair in a chignon",
    "Victory rolls": "her hair in victory rolls",
    "Finger waves": "her hair in finger waves",
    "Pin curls": "her hair in pin curls",
    "Tight curls": "her hair in tight curls",
    "Beach waves": "her hair in beach waves",
    "Slicked back": "her hair in a slicked back style",
    "Wet look": "her hair in a wet look",
    "Beehive": "her hair in a beehive",
    "Pompadour": "her hair in a pompadour",
}

BANGS: Table = {
    "Curtain bangs": "curtain bangs",
    "Side-swept bangs": "side-swept bangs",
    "Wispy bangs": "wispy bangs",
    "Blunt bangs": "blunt bangs",
}

MALE_HAIR_STYLE: Table = {
    "Buzz cut": "a buzz cut",
    "Short crop": "a French crop",
    "High fade": "a high fade",
    "Side part": "a side part",
    "Slicked back": "slicked back hair",
    "Pompadour": "a pompadour",
    "Quiff": "a quiff",
    "Spiky": "spiky hair",
    "Bowl cut": "a bowl cut",
    "Mullet": "a mullet",
    "Man bun": "a man bun",
    "Long hair": "long hair",
    "Afro": "an afro",
    "Cornrows": "cornrows",
    "Dreadlocks": "dreadlocks",
    "Mohawk": "a mohawk",
    "Shaved head": "a shaved head",
    "Receding hairline": "a receding hairline",
    "Balding": "balding hair",
}

# --- Skin -----------------------------------------------------------------

SKIN_TONE: Table = {
    "Porcelain": "very fair porcelain skin",
    "Alabaster": "alabaster skin",
    "Fair": "fair skin",
    "Light": "light skin",
    "Light-medium": "light-medium warm beige skin",
    "Medium golden": "medium golden skin",
    "Olive": "olive skin",
    "Tan": "tan skin",
    "Caramel": "caramel skin",
    "Brown": "brown skin",
    "Dark brown": "dark brown skin",
    "Ebony": "ebony skin",
}

TAN: Table = {
    "Light tan": "a hint of a tan",
    "Deep tan": "deeply tanned skin",
}

FRECKLES: Table = {
    "A few": "a few freckles",
    "Prominent": "prominent freckles",
}

ACNE: Table = {
    "A few blemishes": "a few blemishes",
    "Some acne": "some acne",
    "Pronounced acne": "pronounced acne",
}

BEAUTY_MARK: Table = {
    "Left cheek": "a single beauty mark on the left cheek",
    "Right cheek": "a single beauty mark on the right cheek",
}

DIMPLES: Table = {
    "Subtle": "subtle dimples",
    "Deep": "deep dimples",
}

TATTOO: Table = {
    "Small tattoo": "a small tattoo",
    "Sleeve tattoo": "a sleeve tattoo",
    "Neck tattoo": "a neck tattoo",
    "Hand tattoo": "a hand tattoo",
}

# --- Unclothed detail (used by the prompter only for nude drafts) -----------

NIPPLES: Table = {
    "Large": "large prominent nipples",
    "Puffy": "puffy nipples",
    "Pierced": "pierced nipples",
    "Dark": "dark nipples",
    "Pink": "pink nipples",
}

AREOLA: Table = {
    "Large": "large areolas",
    "Light": "very light areolas",
    "Dark": "dark areolas",
    "Puffy": "puffy areolas",
}
