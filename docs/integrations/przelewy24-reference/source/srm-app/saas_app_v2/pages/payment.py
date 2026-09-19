import reflex as rx
import reflex_chakra
from ..state import State
from ..style import *


def plan_card(plan_id: str, plan_name: str, price: str, unit: str, subtitle: str, features: list, vat_info: str = "", is_best: bool = False):
    """Karty wyboru planu subskrypcji."""
    is_selected = State.selected_plan == plan_id

    return reflex_chakra.box(
        # Badge "Najlepsza oferta"
        rx.cond(
            is_best,
            reflex_chakra.box(
                reflex_chakra.text(
                    "Najlepsza oferta",
                    font_size="9px",
                    font_weight="900",
                    text_transform="uppercase",
                    letter_spacing="0.2em",
                    color="black",
                ),
                position="absolute",
                top="-12px",
                left="50%",
                transform="translateX(-50%)",
                bg=CYBER_YELLOW,
                padding="4px 16px",
                border_radius="full",
            ),
            reflex_chakra.box(),
        ),
        # Plan name
        reflex_chakra.text(
            plan_name,
            font_size="10px",
            font_weight="900",
            text_transform="uppercase",
            letter_spacing="0.3em",
            color="gray.500",
            margin_bottom="0.5rem",
        ),
        # Price
        reflex_chakra.hstack(
            reflex_chakra.text(price, font_size="36px", font_weight="900", color="white"),
            reflex_chakra.vstack(
                reflex_chakra.text("PLN", font_size="14px", font_weight="900", color=CYBER_YELLOW),
                reflex_chakra.text(unit, font_size="10px", font_weight="700", color="gray.500"),
                spacing="0",
                align_items="flex-start",
            ),
            align_items="flex-end",
            spacing="4px",
            margin_bottom="0.5rem",
        ),
        # Subtitle
        reflex_chakra.text(
            subtitle,
            font_size="10px",
            font_weight="700",
            color="gray.500",
            margin_bottom="1.5rem",
        ),
        # Features
        reflex_chakra.vstack(
            *[
                reflex_chakra.hstack(
                    reflex_chakra.text("✓", color=CYBER_YELLOW, font_size="12px", font_weight="900"),
                    reflex_chakra.text(f, font_size="11px", font_weight="700", color="gray.400"),
                    spacing="8px",
                )
                for f in features
            ],
            spacing="8px",
            align_items="flex-start",
        ),
        # VAT info
        reflex_chakra.text(
            vat_info,
            font_size="9px",
            font_weight="700",
            color="gray.600",
            margin_top="1rem",
            text_align="center",
            width="100%",
        ),
        position="relative",
        padding="2rem",
        border_radius="20px",
        border=rx.cond(is_selected, f"2px solid {CYBER_YELLOW}", "2px solid #1a1a1a"),
        bg="linear-gradient(145deg, #0a1415 0%, #000 100%)",
        cursor="pointer",
        transition="all 0.2s",
        _hover={"border_color": CYBER_YELLOW, "box_shadow": YELLOW_GLOW},
        on_click=State.select_plan(plan_id),
    )


def payment_page():
    """Strona wyboru planu subskrypcji."""
    return reflex_chakra.center(
        reflex_chakra.vstack(
            # Header
            reflex_chakra.vstack(
                reflex_chakra.heading(
                    reflex_chakra.span("Manager Przekierowań/", color=CYBER_YELLOW),
                    reflex_chakra.span("GSC 404", color="white"),
                    size="xs",
                    letter_spacing="0.4em",
                    font_weight="900",
                ),
                reflex_chakra.heading(
                    "ODBLOKUJ PEŁNĄ MOC NARZĘDZI SEO",
                    size="md",
                    font_weight="900",
                    text_transform="uppercase",
                    letter_spacing="0.05em",
                ),
                spacing="8px",
                text_align="center",
                margin_bottom="2rem",
            ),
            # Plan cards
            reflex_chakra.hstack(
                plan_card(
                    plan_id="monthly",
                    plan_name="Miesięczny",
                    price="100",
                    unit="/mies.",
                    subtitle="",
                    vat_info="netto + 23,00 PLN VAT = 123,00 PLN brutto",
                    features=[
                        "Pełny dostęp do API",
                        "Przekierowania 301",
                        "Analizy GSC",
                    ],
                    is_best=False,
                ),
                plan_card(
                    plan_id="yearly",
                    plan_name="Roczny",
                    price="50",
                    unit="/mies",
                    subtitle="= 600,00 zł/rocznie · oszczędzasz 600 zł",
                    vat_info="netto + 138,00 PLN VAT = 738,00 PLN brutto/rok",
                    features=[
                        "Pełny dostęp do API",
                        "Przekierowania 301",
                        "Raporty GSC",
                        "Przekierowania 404",
                        "Rabat ~50%",
                    ],
                    is_best=True,
                ),
                spacing="1.5rem",
            ),
            # Pay button
            reflex_chakra.button(
                "Zapłać z Przelewy24",
                width="100%",
                padding="1.5rem",
                margin_top="2rem",
                font_size="13px",
                **button_yellow,
                on_click=State.create_payment,
            ),
            # Error
            rx.cond(
                State.payment_error != "",
                reflex_chakra.box(
                    reflex_chakra.text(
                        State.payment_error,
                        font_size="10px",
                        font_weight="900",
                        text_transform="uppercase",
                        letter_spacing="0.1em",
                        color="red.400",
                    ),
                    padding="0.75rem",
                    bg="rgba(255,0,0,0.1)",
                    border_radius="lg",
                    margin_top="1rem",
                    text_align="center",
                    width="100%",
                ),
                reflex_chakra.box(),
            ),
            # Footer
            reflex_chakra.text(
                "Płatność obsługiwana przez Przelewy24 · Bezpieczna transmisja SSL",
                font_size="9px",
                font_weight="700",
                text_transform="uppercase",
                letter_spacing="0.15em",
                color="gray.700",
                margin_top="1.5rem",
                text_align="center",
            ),
            max_width="640px",
            width="100%",
            **card_style,
        ),
        min_height="100vh",
        bg=BLACK,
    )
