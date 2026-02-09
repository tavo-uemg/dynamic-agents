from typing import Any, Literal, Union

from pydantic import BaseModel, Field


class StyleMixin(BaseModel):
    """Common style properties for all UI components."""

    mt: int | str | None = Field(None, description="Margin top")
    mb: int | str | None = Field(None, description="Margin bottom")
    ml: int | str | None = Field(None, description="Margin left")
    mr: int | str | None = Field(None, description="Margin right")
    p: int | str | None = Field(None, description="Padding")
    w: int | str | None = Field(None, description="Width")
    h: int | str | None = Field(None, description="Height")
    c: str | None = Field(None, description="Color (Mantine color or hex)")
    bg: str | None = Field(None, description="Background color")
    hidden: bool | None = Field(None, description="Hide element")


class Component(StyleMixin):
    """Base class for all UI components."""

    id: str | None = Field(None, description="Unique ID for the component")


# --- Typography ---
class Text(Component):
    type: Literal["text"] = "text"
    content: str
    size: Literal["xs", "sm", "md", "lg", "xl"] | None = None
    weight: Literal["normal", "bold"] | None = None
    align: Literal["left", "center", "right", "justify"] | None = None


class Title(Component):
    type: Literal["title"] = "title"
    content: str
    order: Literal[1, 2, 3, 4, 5, 6] = 1
    align: Literal["left", "center", "right"] | None = None


# --- Actions ---
class Button(Component):
    type: Literal["button"] = "button"
    label: str
    variant: Literal["filled", "light", "outline", "subtle", "white", "default"] = "filled"
    color: str | None = None
    size: Literal["xs", "sm", "md", "lg", "xl"] | None = None
    disabled: bool = False
    loading: bool = False
    action_id: str | None = Field(None, description="ID of action to trigger on click")


# --- Inputs ---
class TextInput(Component):
    type: Literal["text_input"] = "text_input"
    label: str | None = None
    placeholder: str | None = None
    description: str | None = None
    error: str | None = None
    required: bool = False
    name: str = Field(..., description="Form field name")


class NumberInput(Component):
    type: Literal["number_input"] = "number_input"
    label: str | None = None
    min: float | None = None
    max: float | None = None
    name: str = Field(..., description="Form field name")


class Select(Component):
    type: Literal["select"] = "select"
    label: str | None = None
    data: list[str] | list[dict[str, str]]
    name: str = Field(..., description="Form field name")


class Checkbox(Component):
    type: Literal["checkbox"] = "checkbox"
    label: str
    checked: bool = False
    name: str = Field(..., description="Form field name")


# --- Data Display ---
class Badge(Component):
    type: Literal["badge"] = "badge"
    label: str
    color: str | None = None
    variant: Literal["filled", "light", "outline"] = "light"


class Stat(Component):
    type: Literal["stat"] = "stat"
    label: str
    value: str
    diff: float | None = None
    color: str | None = None


class Table(Component):
    type: Literal["table"] = "table"
    headers: list[str]
    rows: list[list[str]]
    striped: bool = False
    highlight_on_hover: bool = False


# --- Charts ---
class ChartSeries(BaseModel):
    name: str
    color: str


class BarChart(Component):
    type: Literal["bar_chart"] = "bar_chart"
    data: list[dict[str, Any]]
    data_key: str
    series: list[ChartSeries]
    title: str | None = None


# --- Layout (Recursive) ---
class Stack(Component):
    type: Literal["stack"] = "stack"
    gap: Literal["xs", "sm", "md", "lg", "xl"] | int | None = None
    align: Literal["stretch", "center", "start", "end"] | None = None
    justify: Literal["center", "start", "end", "space-between"] | None = None
    children: list["UIComponent"]


class Group(Component):
    type: Literal["group"] = "group"
    gap: Literal["xs", "sm", "md", "lg", "xl"] | int | None = None
    align: Literal["stretch", "center", "start", "end"] | None = None
    justify: Literal["center", "start", "end", "space-between"] | None = None
    wrap: Literal["wrap", "nowrap"] | None = None
    children: list["UIComponent"]


class Grid(Component):
    type: Literal["grid"] = "grid"
    cols: int = 1
    children: list["UIComponent"]


class Card(Component):
    type: Literal["card"] = "card"
    shadow: Literal["xs", "sm", "md", "lg", "xl"] | None = "sm"
    padding: Literal["xs", "sm", "md", "lg", "xl"] | None = "md"
    with_border: bool = False
    children: list["UIComponent"]


class Container(Component):
    type: Literal["container"] = "container"
    size: Literal["xs", "sm", "md", "lg", "xl"] | int | None = None
    children: list["UIComponent"]


# --- Union Type ---
UIComponent = Union[
    Text,
    Title,
    Button,
    TextInput,
    NumberInput,
    Select,
    Checkbox,
    Badge,
    Stat,
    Table,
    BarChart,
    Stack,
    Group,
    Grid,
    Card,
    Container,
]


class UISchema(BaseModel):
    """Root object for UI definition."""

    root: UIComponent
    version: int = 1
    theme_mode: Literal["light", "dark", "auto"] = "auto"
