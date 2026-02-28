from fasthtml.common import Div, Input, Label, Option, P, Select, Span, Textarea

_WRAP_CLASS = "mb-4"
_LABEL_CLASS = "block text-sm font-semibold text-slate-800 dark:text-slate-100 mb-1.5"
_HELP_CLASS = "text-xs text-slate-500 dark:text-slate-400 mt-1"
_FIELD_CLASS = (
    "settings-field w-full rounded-xl border px-3 py-2.5 text-slate-800 dark:text-slate-100 "
    "bg-white/90 dark:bg-slate-900/80 border-slate-300 dark:border-slate-700 "
    "placeholder:text-slate-500/70 dark:placeholder:text-slate-400/70 "
    "outline-none transition"
)


def _val_or_default(val, default=""):
    return "" if val is None else val


def setting_input(label, key, value, input_type="text", help_text="", **attrs):
    """Generic input setting control."""
    attrs_str = {}
    attrs_str.update(attrs)
    return Div(
        Label(label, cls=_LABEL_CLASS),
        Input(
            type=input_type,
            name=key,
            value=_val_or_default(value),
            cls=_FIELD_CLASS,
            **attrs_str,
        ),
        P(help_text, cls=_HELP_CLASS) if help_text else "",
        cls=_WRAP_CLASS,
    )


def setting_number(label, key, value, help_text="", min_val=None, max_val=None, step_val=None):
    """Numeric input setting control."""
    attrs = {}
    if min_val is not None:
        attrs["min"] = min_val
    if max_val is not None:
        attrs["max"] = max_val
    if step_val is not None:
        attrs["step"] = step_val
    return setting_input(label, key, value, input_type="number", help_text=help_text, **attrs)


def setting_range(label, key, value, help_text="", min_val=0, max_val=100, step_val=1.0):
    """Range slider setting control."""
    slider = Input(
        type="range",
        name=key,
        value=_val_or_default(value),
        min=min_val,
        max=max_val,
        step=step_val,
        cls="settings-range w-full cursor-pointer",
        oninput="this.nextElementSibling && (this.nextElementSibling.textContent = this.value)",
    )
    display = Span(
        str(_val_or_default(value) or ""),
        cls=(
            "inline-flex min-w-12 justify-center px-2 py-1 rounded-full text-xs font-semibold tabular-nums "
            "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 "
            "border border-slate-200 dark:border-slate-700"
        ),
    )
    return Div(
        Label(label, cls=_LABEL_CLASS),
        Div(slider, display, cls="flex items-center gap-3"),
        P(help_text, cls=_HELP_CLASS) if help_text else "",
        cls=_WRAP_CLASS,
    )


def setting_color(label, key, value, help_text=""):
    """Color picker setting control."""
    return Div(
        Label(label, cls=_LABEL_CLASS),
        Div(
            Input(
                type="color",
                name=key,
                value=_val_or_default(value) or "#ffffff",
                cls="settings-color-picker h-11 w-20 p-1 border border-slate-300 dark:border-slate-700 rounded-xl",
                oninput="this.nextElementSibling && (this.nextElementSibling.textContent = this.value)",
            ),
            Span(
                _val_or_default(value) or "#ffffff",
                cls=(
                    "text-xs font-mono px-2 py-1 rounded-full bg-slate-100 dark:bg-slate-800 "
                    "text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700"
                ),
            ),
            cls="flex items-center gap-3",
        ),
        P(help_text, cls=_HELP_CLASS) if help_text else "",
        cls=_WRAP_CLASS,
    )


def setting_toggle(label, key, value, help_text=""):
    """Checkbox toggle setting control."""
    checked = "checked" if value else None
    return Div(
        Label(label, cls=_LABEL_CLASS),
        Input(type="hidden", name=key, value="false"),
        Label(
            Input(
                type="checkbox",
                name=key,
                checked=checked,
                value="true",
                cls="settings-checkbox h-6 w-6 rounded-md border border-slate-400 dark:border-slate-500 shrink-0",
            ),
            Span("Abilitato", cls="text-sm font-medium text-slate-800 dark:text-slate-100"),
            cls="inline-flex items-center gap-3 select-none cursor-pointer",
        ),
        P(help_text, cls=_HELP_CLASS) if help_text else "",
        cls=_WRAP_CLASS,
    )


def setting_select(label, key, value, options, help_text=""):
    """Dropdown select setting control."""
    opts = []
    for v, label_text in options:
        opts.append(Option(label_text, value=v, selected=(v == value)))
    return Div(
        Label(label, cls=_LABEL_CLASS),
        Select(*opts, name=key, cls=_FIELD_CLASS),
        P(help_text, cls=_HELP_CLASS) if help_text else "",
        cls=_WRAP_CLASS,
    )


def setting_textarea(label, key, value, help_text=""):
    """Textarea setting control."""
    return Div(
        Label(label, cls=_LABEL_CLASS),
        Textarea(
            _val_or_default(value),
            name=key,
            cls=f"{_FIELD_CLASS} h-24",
        ),
        P(help_text, cls=_HELP_CLASS) if help_text else "",
        cls=_WRAP_CLASS,
    )


raw_init = (
    "<script>"
    "document.querySelectorAll('[data_pane],[data-pane]').forEach((p,i)=>{p.style.display=(i===0?'block':'none')});"
    "var ft=document.querySelector('[data_tab]')||document.querySelector('[data-tab]');"
    "if(ft)ft.classList.add('settings-tab-active');"
    "</script>"
)

raw_file_script = (
    "<script>"
    "document.querySelectorAll('input[type=file][data-target-id],input[type=file][data_target_id]')"
    ".forEach(function(fi){"
    " fi.addEventListener('change', function(){try{"
    " var tid=this.getAttribute('data-target-id')||this.getAttribute('data_target_id');"
    " if(!tid) return; var target=document.getElementById(tid); if(!target) return;"
    " target.value=(this.files && this.files.length)?this.files[0].name:'';}"
    " catch(err){console.warn('file->path bind',err)}});"
    "});"
    "</script>"
)
