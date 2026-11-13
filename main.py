"""Stoichiometry Assistant

The user enters a balanced equation, the starting mass of each reactant,
the actual mass of product collected, and the reaction enthalpy. The site
reports the limiting reactant, theoretical yield, percent yield, leftover
reactants, and whether the reaction is exothermic or endothermic.

Required for format:
    -put a space between a coefficient and its formula
    -simple formulas only (like H2O, NaCl, CO2); no parentheses
Example format: "2 H2 + O2 -> 2 H2O"
"""
from dataclasses import dataclass
from bakery import assert_equal
from drafter import *
ATOMIC_MASSES = {
    "H": 1.008, "He": 4.0026, "Li": 6.94, "Be": 9.0122, "B": 10.81,
    "C": 12.011, "N": 14.007, "O": 15.999, "F": 18.998, "Ne": 20.180,
    "Na": 22.990, "Mg": 24.305, "Al": 26.982, "Si": 28.085, "P": 30.974,
    "S": 32.06, "Cl": 35.45, "Ar": 39.948, "K": 39.098, "Ca": 40.078,
    "Fe": 55.845, "Cu": 63.546, "Zn": 65.38, "Br": 79.904, "Ag": 107.87,
    "I": 126.90, "Au": 196.97, "Hg": 200.59, "Pb": 207.2,}

@dataclass
class Chemical:
    """Chemicals in the equation"""
    formula: str
    coefficient: int
    mass_g: float
    molar_mass: float
    moles: float

@dataclass
class State:
    """Used for website memory"""
    equation: str
    reactants: list[Chemical]
    products: list[Chemical]
    product_formula: str
    actual_yield_g: float
    enthalpy_kj: float
    limiting_reactant: str
    theoretical_yield_g: float
    percent_yield: float
    current_index: int  
    error_message: str


def new_state() -> State:
    """Make a fresh, empty State."""
    return State("", [], [], "", 0.0, 0.0, "", 0.0, 0.0, 0, "")



def molar_mass_of(formula: str) -> float:
    """Return the molar mass of a simple formula like 'H2O'.

    Returns 0.0 if the formula is empty or has an unknown element.
    """
    total = 0.0
    index = 0
    while index < len(formula):
        if not formula[index].isupper():
            return 0.0
        symbol = formula[index]
        index += 1
        if index < len(formula) and formula[index].islower():
            symbol = symbol + formula[index]
            index += 1
        digits = ""
        while index < len(formula) and formula[index].isdigit():
            digits = digits + formula[index]
            index += 1
        if symbol not in ATOMIC_MASSES:
            return 0.0
        atom_count = 1
        if digits != "":
            atom_count = int(digits)
        total = total + ATOMIC_MASSES[symbol] * atom_count
    return total


def parse_term(term: str) -> Chemical:
    """Turn a term like '2 H2O' into a Reactant (coefficient 2, formula H2O)."""
    words = term.split()
    coefficient = 1
    formula = ""
    if len(words) == 1:
        formula = words[0]
    elif len(words) == 2 and words[0].isdigit():
        coefficient = int(words[0])
        formula = words[1]
    if coefficient < 1:
        formula = ""  
    return Chemical(formula, coefficient, 0.0, molar_mass_of(formula), 0.0)


def parse_side(side: str) -> list[Chemical]:
    """Turn one side of the equation, like '2 H2 + O2', into a list."""
    substances = []
    for term in side.split("+"):
        substances.append(parse_term(term))
    return substances


def all_readable(substances: list[Chemical]) -> bool:
    """True if every substance has a molar mass (so it was read correctly)."""
    for substance in substances:
        if substance.molar_mass == 0.0:
            return False
    return True


def is_number(text: str) -> bool:
    """True if the text looks like a number such as '12', '3.5', or '-571.6'."""
    cleaned = text.strip()
    if cleaned.startswith("-"):
        cleaned = cleaned[1:]
    return cleaned.replace(".", "", 1).isdigit()


def is_positive_number(text: str) -> bool:
    """True if the text is a number greater than zero."""
    return is_number(text) and float(text) > 0


def find_limiting_reactant(reactants: list[Chemical]) -> Chemical:
    """Return the reactant with the smallest moles / coefficient ratio."""
    limiting = reactants[0]
    smallest_ratio = limiting.moles / limiting.coefficient
    for r in reactants:
        ratio = r.moles / r.coefficient
        if ratio < smallest_ratio:
            smallest_ratio = ratio
            limiting = r
    return limiting


def find_product(products: list[Chemical], formula: str) -> Chemical:
    """Return the product with this formula (the first one if not found)."""
    for product in products:
        if product.formula == formula:
            return product
    return products[0]


def leftover_grams(reactant: Chemical, times_reaction_runs: float) -> float:
    """Grams of a reactant left over after the reaction runs."""
    moles_used = times_reaction_runs * reactant.coefficient
    leftover = (reactant.moles - moles_used) * reactant.molar_mass
    if leftover < 0:
        return 0.0  
    return leftover


def calculate_percent_yield(actual_g: float, theoretical_g: float) -> float:
    """Percent yield = actual / theoretical * 100."""
    return actual_g / theoretical_g * 100


def classify_enthalpy(enthalpy_kj: float) -> str:
    """Say whether a reaction is exothermic or endothermic."""
    if enthalpy_kj < 0:
        return "exothermic"
    elif enthalpy_kj > 0:
        return "endothermic"
    return "neither (no heat change)"



@route
def index(state: State) -> Page:
    """Home page."""
    return Page(state, [
        Header("Stoichiometry Assistant", 1),
        "Enter a balanced equation, your starting masses, and the product "
        "you collected. I will find the limiting reactant, theoretical and "
        "percent yield, leftover reactants, and whether the reaction is "
        "exothermic or endothermic.",
        Button("Start", enter_equation),
    ])


@route
def enter_equation(state: State) -> Page:
    """Page where the user types the balanced equation."""
    return Page(state, [
        Header("Step 1: Balanced equation", 1),
        "Example: 2 H2 + O2 -> 2 H2O",
        "Put a space between each coefficient and formula. The equation "
        "must already be balanced.",
        TextBox("equation", state.equation),
        Button("Continue", submit_equation),
        Button("Back", index),
    ])


@route
def submit_equation(state: State, equation: str) -> Page:
    """Read the equation and save the reactants and products."""
    sides = equation.split("->")
    if len(sides) != 2:
        state.error_message = "The equation needs exactly one arrow (->)."
        return show_error(state)
    reactants = parse_side(sides[0])
    products = parse_side(sides[1])
    if not all_readable(reactants) or not all_readable(products):
        state.error_message = ("I could not read that equation. Check the "
                               "spaces, element symbols, and capital letters.")
        return show_error(state)
    state.equation = equation
    state.reactants = reactants
    state.products = products
    state.product_formula = products[0].formula
    state.current_index = 0
    return enter_masses(state)


@route
def enter_masses(state: State) -> Page:
    """Ask for the starting mass of ONE reactant (the current one)."""
    reactant = state.reactants[state.current_index]
    return Page(state, [
        Header("Step 2: Starting masses", 1),
        f"Reactant {state.current_index + 1} of {len(state.reactants)}: "
        f"{reactant.formula} (molar mass {reactant.molar_mass:.3f} g/mol)",
        "Starting mass in grams:",
        TextBox("mass_text", ""),
        Button("Next", submit_masses),
    ])


@route
def submit_masses(state: State, mass_text: str) -> Page:
    """Save the current reactant's mass and moles, then move on."""
    if not is_positive_number(mass_text):
        state.error_message = "The mass must be a number greater than zero."
        return show_error(state)
    reactant = state.reactants[state.current_index]
    reactant.mass_g = float(mass_text)
    reactant.moles = reactant.mass_g / reactant.molar_mass
    state.current_index += 1
    if state.current_index < len(state.reactants):
        return enter_masses(state)
    return enter_yield_energy(state)


@route
def enter_yield_energy(state: State) -> Page:
    """Page for the product choice, actual yield, and enthalpy."""
    product_options = []
    for product in state.products:
        product_options.append(product.formula)
    return Page(state, [
        Header("Step 3: Yield and energy", 1),
        "Which product did you collect?",
        SelectBox("product_formula", product_options, state.product_formula),
        "Actual mass of that product collected (grams):",
        TextBox("actual_yield_text", ""),
        "Reaction enthalpy in kJ (negative means heat is released):",
        TextBox("enthalpy_text", ""),
        Button("Calculate", submit_yield_energy),
    ])


@route
def submit_yield_energy(state: State, product_formula: str,
                        actual_yield_text: str, enthalpy_text: str) -> Page:
    """Check and save the product choice, actual yield, and enthalpy."""
    if not is_positive_number(actual_yield_text):
        state.error_message = "The actual yield must be a number above zero."
        return show_error(state)
    if not is_number(enthalpy_text):
        state.error_message = "The enthalpy must be a number (like -571.6)."
        return show_error(state)
    state.product_formula = product_formula
    state.actual_yield_g = float(actual_yield_text)
    state.enthalpy_kj = float(enthalpy_text)
    return show_results(state)


@route
def show_results(state: State) -> Page:
    """Do the calculations and show the results."""
    limiting = find_limiting_reactant(state.reactants)
    times_reaction_runs = limiting.moles / limiting.coefficient
    product = find_product(state.products, state.product_formula)
    theoretical_moles = times_reaction_runs * product.coefficient

    state.limiting_reactant = limiting.formula
    state.theoretical_yield_g = theoretical_moles * product.molar_mass
    state.percent_yield = calculate_percent_yield(
        state.actual_yield_g, state.theoretical_yield_g)

    reaction_type = classify_enthalpy(state.enthalpy_kj)
    heat_per_mole = state.enthalpy_kj / product.coefficient
    summary = [
        f"Limiting reactant: {limiting.formula}",
        f"Theoretical yield of {product.formula}: {theoretical_moles:.4f} mol "
        f"({state.theoretical_yield_g:.3f} g)",
        f"Actual yield: {state.actual_yield_g:.3f} g",
        f"Percent yield: {state.percent_yield:.1f}%",
        f"Reaction type: {reaction_type}",
        f"Heat per mole of {product.formula}: {heat_per_mole:.2f} kJ/mol",
    ]
    leftovers = []
    for reactant in state.reactants:
        grams = leftover_grams(reactant, times_reaction_runs)
        leftovers.append(f"{reactant.formula}: {grams:.3f} g remaining")

    content = [Header("Results", 1), BulletedList(summary),
               Header("Leftover reactants", 2), BulletedList(leftovers)]
    if state.percent_yield > 100:
        content.append("Warning: a percent yield above 100% usually means "
                       "a measurement error.")
    content.append(Button("Change yield/energy", enter_yield_energy))
    content.append(Button("Start over", reset_state))
    return Page(state, content)


@route
def show_error(state: State) -> Page:
    """Error page that shows the saved error message."""
    return Page(state, [
        Header("Something went wrong", 1),
        state.error_message,
        Button("Try again", enter_equation),
        Button("Start over", reset_state),
    ])


@route
def reset_state(state: State) -> Page:
    """Erase all saved data and go back to the home page."""
    return index(new_state())

assert_equal(round(molar_mass_of("H2O"), 3), 18.015)
assert_equal(round(molar_mass_of("NaCl"), 2), 58.44)
assert_equal(molar_mass_of("Xx2"), 0.0)
assert_equal(parse_term("2 H2O").coefficient, 2)
assert_equal(parse_term("O2").coefficient, 1)
assert_equal(len(parse_side("2 H2 + O2")), 2)
assert_equal(is_number("-571.6"), True)
assert_equal(is_number("abc"), False)
assert_equal(is_positive_number("-5"), False)
assert_equal(calculate_percent_yield(9.0, 18.0), 50.0)
assert_equal(classify_enthalpy(-286.0), "exothermic")
assert_equal(classify_enthalpy(50.0), "endothermic")
assert_equal(leftover_grams(Chemical("O2", 1, 32.0, 32.0, 1.0), 0.5), 16.0)

_h2 = Chemical("H2", 2, 4.0, 2.016, 4.0 / 2.016)
_o2 = Chemical("O2", 1, 32.0, 31.998, 32.0 / 31.998)
assert_equal(find_limiting_reactant([_o2, _h2]).formula, "H2")
assert_equal(find_product([Chemical("H2O", 2, 0.0, 18.0, 0.0)], "X").formula,
             "H2O")
_test_state = new_state()
submit_equation(_test_state, "2 H2 + O2 -> 2 H2O")
assert_equal(len(_test_state.reactants), 2)
assert_equal(_test_state.product_formula, "H2O")
submit_masses(_test_state, "4.0")
assert_equal(_test_state.current_index, 1)
submit_masses(_test_state, "32.0")
submit_yield_energy(_test_state, "H2O", "30.0", "-571.6")
assert_equal(_test_state.limiting_reactant, "H2")
assert_equal(round(_test_state.theoretical_yield_g, 2), 35.74)
assert_equal(round(_test_state.percent_yield, 1), 83.9)

_bad_state = new_state()
submit_equation(_bad_state, "H2 + O2") 
assert_equal(_bad_state.error_message != "", True)
submit_masses(_test_state, "-5")
assert_equal(_test_state.error_message, "The mass must be a number greater than zero.")

set_site_information(
    author="James Sutter (jahames@udel.edu)",
    description="Calculates limiting reactant, theoretical and percent yield, "
                "leftover reactants, and reaction type from a balanced equation.",
    sources=["Chemistry 2e (OpenStax), Chapter 4: Stoichiometry"],
    planning=["planning/week10_brainstorm.docx", "planning/week11_design.docx"],
    links=[],
)
set_website_title("Stoichiometry Assistant")
start_server(new_state())
