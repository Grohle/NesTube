"""
nestify/models.py
Dataclasses and enumerations for Nestify.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


# ── Enumerations ─────────────────────────────────────────────────────────────

class TipoPerfil(str, Enum):
    REDONDO     = "redondo"
    RECTANGULAR = "rectangular"
    L           = "L"
    U           = "U"
    H           = "H"


# ── Cut model ────────────────────────────────────────────────────────────────

@dataclass
class Corte:
    descripcion: str  = ""
    largo:       float = 0.0   # mm
    cantidad:    int   = 1
    inglete1:    bool  = False
    inglete2:    bool  = False
    inglete1_dir: str  = "up"   # up | down
    inglete2_dir: str  = "up"   # up | down
    inglete1_deg: float = 45.0
    inglete2_deg: float = 45.0

    def es_valido(self) -> bool:
        return self.largo > 0 and self.cantidad > 0

    def to_dict(self) -> dict:
        return {
            "descripcion": self.descripcion,
            "largo":       self.largo,
            "cantidad":    self.cantidad,
            "inglete1":    self.inglete1,
            "inglete2":    self.inglete2,
            "inglete1_dir": self.inglete1_dir,
            "inglete2_dir": self.inglete2_dir,
            "inglete1_deg": self.inglete1_deg,
            "inglete2_deg": self.inglete2_deg,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Corte":
        return cls(
            descripcion=str(d.get("descripcion", "")),
            largo=float(d.get("largo", 0)),
            cantidad=int(d.get("cantidad", 1)),
            inglete1=bool(d.get("inglete1", False)),
            inglete2=bool(d.get("inglete2", False)),
            inglete1_dir=str(d.get("inglete1_dir", "up")),
            inglete2_dir=str(d.get("inglete2_dir", "up")),
            inglete1_deg=float(d.get("inglete1_deg", 45)),
            inglete2_deg=float(d.get("inglete2_deg", 45)),
        )


# ── Profile configuration ─────────────────────────────────────────────────────

@dataclass
class PerfilDimensiones:
    tipo:         Optional[TipoPerfil] = None
    diametro:     float = 0.0
    lado_a:       float = 0.0
    lado_b:       float = 0.0
    lado_c:       float = 0.0
    espesor:      float = 0.0
    espesor_int_H: float = 0.0
    macizo:       bool  = False
    extra_dims:   Dict[str, float] = field(default_factory=dict)


@dataclass
class ParametrosMaterial:
    peso_especifico:  float = 7.85   # t/m³
    precio_kg:        float = 0.0
    precio_m2:        float = 0.0
    precio_m:         float = 0.0
    kg_por_m:         float = 0.0
    precio_barra:     float = 0.0
    margen_beneficio: float = 0.0    # % profit margin
    repartir_retales: bool  = False


@dataclass
class ParametrosManoObra:
    tiempo_corte_recto:  float = 3.0    # min
    porcentaje_inglete:  float = 35.0   # %
    coste_operario_hora: float = 30.0   # €/h


@dataclass
class ConfigPerfil:
    dimensiones: PerfilDimensiones = field(default_factory=PerfilDimensiones)
    material:    ParametrosMaterial = field(default_factory=ParametrosMaterial)
    mano_obra:   ParametrosManoObra = field(default_factory=ParametrosManoObra)

    def to_dict(self) -> dict:
        d = self.dimensiones
        m = self.material
        mo = self.mano_obra
        return {
            "tipo":              d.tipo.value if d.tipo else None,
            "diametro":         d.diametro,
            "lado_a":           d.lado_a,
            "lado_b":           d.lado_b,
            "lado_c":           d.lado_c,
            "espesor":          d.espesor,
            "espesor_int_H":    d.espesor_int_H,
            "macizo":           d.macizo,
            "extra_dims":       d.extra_dims,
            "peso_especifico":  m.peso_especifico,
            "precio_kg":        m.precio_kg,
            "precio_m2":        m.precio_m2,
            "precio_m":         m.precio_m,
            "kg_por_m":         m.kg_por_m,
            "precio_barra":     m.precio_barra,
            "margen_beneficio": m.margen_beneficio,
            "repartir_retales": m.repartir_retales,
            "tiempo_corte_recto":  mo.tiempo_corte_recto,
            "porcentaje_inglete":  mo.porcentaje_inglete,
            "coste_operario_hora": mo.coste_operario_hora,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ConfigPerfil":
        raw_tipo = d.get("tipo")
        try:
            tipo = TipoPerfil(raw_tipo) if raw_tipo else None
        except ValueError:
            tipo = None
        return cls(
            dimensiones=PerfilDimensiones(
                tipo=tipo,
                diametro=float(d.get("diametro", 0)),
                lado_a=float(d.get("lado_a", 0)),
                lado_b=float(d.get("lado_b", 0)),
                lado_c=float(d.get("lado_c", 0)),
                espesor=float(d.get("espesor", 0)),
                espesor_int_H=float(d.get("espesor_int_H", 0)),
                macizo=bool(d.get("macizo", False)),
                extra_dims=dict(d.get("extra_dims", {})),
            ),
            material=ParametrosMaterial(
                peso_especifico=float(d.get("peso_especifico", 7.85)),
                precio_kg=float(d.get("precio_kg", 0)),
                precio_m2=float(d.get("precio_m2", 0)),
                precio_m=float(d.get("precio_m", 0)),
                kg_por_m=float(d.get("kg_por_m", 0)),
                precio_barra=float(d.get("precio_barra", 0)),
                margen_beneficio=float(d.get("margen_beneficio", 0)),
                repartir_retales=bool(d.get("repartir_retales", False)),
            ),
            mano_obra=ParametrosManoObra(
                tiempo_corte_recto=float(d.get("tiempo_corte_recto", 3)),
                porcentaje_inglete=float(d.get("porcentaje_inglete", 35)),
                coste_operario_hora=float(d.get("coste_operario_hora", 30)),
            ),
        )


# ── Result model ──────────────────────────────────────────────────────────────

@dataclass
class ResultadoCorte:
    descripcion:       str
    largo:             float
    cantidad:          int
    kg_ud:             float
    m2_ud:             float
    precio_material_ud: float
    coste_mano_obra_ud: float

    @property
    def precio_total_ud(self) -> float:
        return self.precio_material_ud + self.coste_mano_obra_ud

    @property
    def precio_m(self) -> float:
        return self.precio_material_ud * 1000 / self.largo if self.largo > 0 else 0.0

    @property
    def precio_total_linea(self) -> float:
        return self.precio_total_ud * self.cantidad


# ── Shared application state ──────────────────────────────────────────────────

@dataclass
class MaterialContext:
    """One material sub-tab: its own cuts, nesting, profile/cost config."""
    name: str = ""
    custom_display_name: str = ""
    profile_name: str = ""
    material: str = ""
    quality: str = ""
    cortes: List = field(default_factory=list)
    barras_necesarias: List = field(default_factory=list)
    nesting_layout: List = field(default_factory=list)
    nesting_bar_lengths: List = field(default_factory=list)
    perfil: ConfigPerfil = field(default_factory=ConfigPerfil)
    longitud_barra: float = 6000.0
    perdida_corte: float = 2.0
    margen_tubo: float = 0.0
    aprovechar_inglete: bool = False
    nesting_height_override: Optional[float] = None
    nesting_mode: str = "simple"
    nesting_strategy: str = "length"
    use_stock: bool = False
    auto_stock: bool = False
    linked_stock_bar_id: Optional[str] = None
    linked_stock_bar_name: str = ""
    nesting_bars_deducted: int = 0
    profile_key: str = ""
    # Per-tab user-defined extra columns for the cut list (Cuts tab). Previously
    # written as a dynamic attribute and lost on save/reload — now a real field.
    custom_fields: Dict[str, str] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        if self.custom_display_name:
            return self.custom_display_name
        from .naming import format_material
        return format_material(self.material, self.quality) or self.name

    @property
    def full_name(self) -> str:
        """Canonical "profile · material · quality" representation (TODO §0)."""
        from .naming import format_full_name
        return format_full_name(self.profile_name, self.material, self.quality)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "custom_display_name": self.custom_display_name,
            "profile_name": self.profile_name,
            "material": self.material,
            "quality": self.quality,
            "cortes": [c.to_dict() if hasattr(c, 'to_dict') else c for c in self.cortes],
            "barras_necesarias": self.barras_necesarias,
            "nesting_layout": self.nesting_layout,
            "nesting_bar_lengths": self.nesting_bar_lengths,
            "perfil": self.perfil.to_dict(),
            "longitud_barra": self.longitud_barra,
            "perdida_corte": self.perdida_corte,
            "margen_tubo": self.margen_tubo,
            "aprovechar_inglete": self.aprovechar_inglete,
            "nesting_height_override": self.nesting_height_override,
            "nesting_mode": self.nesting_mode,
            "nesting_strategy": self.nesting_strategy,
            "use_stock": self.use_stock,
            "auto_stock": self.auto_stock,
            "linked_stock_bar_id": self.linked_stock_bar_id,
            "linked_stock_bar_name": self.linked_stock_bar_name,
            "nesting_bars_deducted": self.nesting_bars_deducted,
            "profile_key": self.profile_key,
            "custom_fields": dict(self.custom_fields),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MaterialContext":
        h_raw = d.get("nesting_height_override")
        return cls(
            name=str(d.get("name", "")),
            custom_display_name=str(d.get("custom_display_name", "")),
            profile_name=str(d.get("profile_name", "")),
            material=str(d.get("material", "")),
            quality=str(d.get("quality", "")),
            cortes=[Corte.from_dict(c) for c in d.get("cortes", [])],
            barras_necesarias=list(d.get("barras_necesarias", [])),
            nesting_layout=list(d.get("nesting_layout", [])),
            nesting_bar_lengths=list(d.get("nesting_bar_lengths", [])),
            perfil=ConfigPerfil.from_dict(d.get("perfil", {})),
            longitud_barra=float(d.get("longitud_barra", 6000)),
            perdida_corte=float(d.get("perdida_corte", 2)),
            margen_tubo=float(d.get("margen_tubo", 0)),
            aprovechar_inglete=bool(d.get("aprovechar_inglete", False)),
            nesting_height_override=float(h_raw) if h_raw is not None else None,
            nesting_mode=str(d.get("nesting_mode", "simple")),
            nesting_strategy=str(d.get("nesting_strategy", "length")),
            use_stock=bool(d.get("use_stock", False)),
            auto_stock=bool(d.get("auto_stock", False)),
            linked_stock_bar_id=d.get("linked_stock_bar_id"),
            linked_stock_bar_name=str(d.get("linked_stock_bar_name", "")),
            nesting_bars_deducted=int(d.get("nesting_bars_deducted", 0)),
            profile_key=str(d.get("profile_key", "")),
            custom_fields=dict(d.get("custom_fields", {})),
        )


def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


@dataclass
class AppState:
    longitud_barra:    float = 6000.0
    perdida_corte:     float = 2.0
    margen_tubo:       float = 0.0
    aprovechar_inglete: bool = False
    descripcion:       str   = ""
    calidad:           str   = ""
    pedido:            str   = ""
    oferta:            str   = ""
    cliente:           str   = ""
    cortes:            list  = field(default_factory=list)
    barras_necesarias: list  = field(default_factory=list)
    nesting_layout:    list  = field(default_factory=list)
    nesting_bar_lengths: list = field(default_factory=list)
    perfil:            ConfigPerfil = field(default_factory=ConfigPerfil)
    export_path:       str   = ""
    custom_fields:     Dict[str, str] = field(default_factory=dict)
    language:          str   = "es"
    calc_system:       str   = "ffd"
    currency:          str   = "EUR"
    custom_profile_types: List[str] = field(default_factory=list)
    material_contexts: List[MaterialContext] = field(default_factory=list)
    active_material_index: int = 0
    nesting_height_override: Optional[float] = None
    nesting_mode: str = "simple"
    nesting_strategy: str = "length"
    active_tab: int = 0

    def reset_from(self, other: "AppState") -> None:
        for key, value in other.__dict__.items():
            setattr(self, key, value)

    def to_dict(self) -> dict:
        return {
            "longitud_barra":  self.longitud_barra,
            "perdida_corte":   self.perdida_corte,
            "margen_tubo":     self.margen_tubo,
            "aprovechar_inglete": self.aprovechar_inglete,
            "descripcion":     self.descripcion,
            "calidad":         self.calidad,
            "pedido":          self.pedido,
            "oferta":          self.oferta,
            "cliente":         self.cliente,
            "cortes":          [c.to_dict() for c in self.cortes],
            "barras_necesarias": self.barras_necesarias,
            "perfil":          self.perfil.to_dict(),
            "nesting_layout":  self.nesting_layout,
            "nesting_bar_lengths": self.nesting_bar_lengths,
            "export_path":     self.export_path,
            "custom_fields":   self.custom_fields,
            "language":        self.language,
            "calc_system":     self.calc_system,
            "currency":        self.currency,
            "custom_profile_types": self.custom_profile_types,
            "material_contexts": [mc.to_dict() for mc in self.material_contexts],
            "active_material_index": self.active_material_index,
            "nesting_height_override": self.nesting_height_override,
            "nesting_mode": self.nesting_mode,
            "nesting_strategy": self.nesting_strategy,
            "active_tab": self.active_tab,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AppState":
        return cls(
            longitud_barra=float(d.get("longitud_barra", 6000)),
            perdida_corte=float(d.get("perdida_corte", 2)),
            margen_tubo=float(d.get("margen_tubo", 0)),
            aprovechar_inglete=bool(d.get("aprovechar_inglete", False)),
            descripcion=str(d.get("descripcion", "")),
            calidad=str(d.get("calidad", "")),
            pedido=str(d.get("pedido", "")),
            oferta=str(d.get("oferta", "")),
            cliente=str(d.get("cliente", "")),
            cortes=[Corte.from_dict(c) for c in d.get("cortes", [])],
            barras_necesarias=list(d.get("barras_necesarias", [])),
            perfil=ConfigPerfil.from_dict(d.get("perfil", {})),
            nesting_layout=list(d.get("nesting_layout", [])),
            nesting_bar_lengths=list(d.get("nesting_bar_lengths", [])),
            export_path=str(d.get("export_path", "")),
            custom_fields=dict(d.get("custom_fields", {})),
            language=str(d.get("language", "es")),
            calc_system=str(d.get("calc_system", "ffd")),
            currency=str(d.get("currency", "EUR")),
            custom_profile_types=list(d.get("custom_profile_types", [])),
            material_contexts=[
                MaterialContext.from_dict(mc)
                for mc in d.get("material_contexts", [])
            ],
            active_material_index=int(d.get("active_material_index", 0)),
            nesting_height_override=_safe_float(d.get("nesting_height_override")),
            nesting_mode=str(d.get("nesting_mode", "simple")),
            nesting_strategy=str(d.get("nesting_strategy", "length")),
            active_tab=int(d.get("active_tab", 0)),
        )
