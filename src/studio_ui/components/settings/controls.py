from fasthtml.common import Div, Input, Label, Option, P, Select, Span, Textarea


def _val_or_default(val, default=""):
    return "" if val is None else val


def setting_input(label, key, value, input_type="text", help_text="", **attrs):
    """Generic input setting control."""
    attrs_str = {}
    attrs_str.update(attrs)
    return Div(
        Label(label, cls="block text-sm font-medium text-slate-300 mb-1"),
        Input(
            type=input_type,
            name=key,
            value=_val_or_default(value),
            cls=(
                "w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100 "
                " focus:border-blue-500 outline-none transition-colors"
            ),
            **attrs_str,
        ),
        P(help_text, cls="text-xs text-slate-500 mt-1") if help_text else "",
        cls="mb-4",
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
        cls=(
            "w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100 "
            "focus:border-blue-500 outline-none transition-colors"
        ),
        oninput="this.nextElementSibling && (this.nextElementSibling.textContent = this.value)",
    )
    display = Span(str(_val_or_default(value) or ""), cls="ml-3 text-sm text-slate-300")
    return Div(
        Label(label, cls="block text-sm font-medium text-slate-300 mb-1"),
        slider,
        display,
        P(help_text, cls="text-xs text-slate-500 mt-1") if help_text else "",
        cls="mb-4",
    )


def setting_color(label, key, value, help_text=""):
    """Color picker setting control."""
    return Div(
        Label(label, cls="block text-sm font-medium text-slate-300 mb-1"),
        Input(type="color", name=key, value=_val_or_default(value) or "#ffffff", cls="h-10 w-16 p-0"),
        P(help_text, cls="text-xs text-slate-500 mt-1") if help_text else "",
        cls="mb-4",
    )


def setting_toggle(label, key, value, help_text=""):
    """Checkbox toggle setting control."""
    checked = "checked" if value else None
    return Div(
        Label(label, cls="block text-sm font-medium text-slate-300 mb-1"),
        Input(type="hidden", name=key, value="false"),
        Input(type="checkbox", name=key, checked=checked, value="true", cls="mr-2"),
        P(help_text, cls="text-xs text-slate-500 mt-1") if help_text else "",
        cls="mb-4",
    )


def setting_select(label, key, value, options, help_text=""):
    """Dropdown select setting control."""
    opts = []
    for v, label_text in options:
        opts.append(Option(label_text, value=v, selected=(v == value)))
    return Div(
        Label(label, cls="block text-sm font-medium text-slate-300 mb-1"),
        Select(*opts, name=key, cls="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100"),
        P(help_text, cls="text-xs text-slate-500 mt-1") if help_text else "",
        cls="mb-4",
    )


def setting_textarea(label, key, value, help_text=""):
    """Textarea setting control."""
    return Div(
        Label(label, cls="block text-sm font-medium text-slate-300 mb-1"),
        Textarea(
            _val_or_default(value),
            name=key,
            cls="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-100 h-24",
        ),
        P(help_text, cls="text-xs text-slate-500 mt-1") if help_text else "",
        cls="mb-4",
    )


# Small raw HTML injections (split strings for line length)
raw_init = (
    "<script>"
    "document.querySelectorAll('[data_pane],[data-pane]').forEach((p,i)=>{p.style.display=(i===0?'block':'none')});"
    "var ft=document.querySelector('[data_tab]')||document.querySelector('[data-tab]'); "
    "if(ft)ft.classList.add('bg-slate-700');"
    "</script>"
)

raw_file_script = (
    "<script>"
    "document.querySelectorAll('input[type=file][data-target-id],input[type=file][data_target_id]').forEach(function(fi){"
    " fi.addEventListener('change', function(e){try{var tid=this.getAttribute('data-target-id') || "
    " this.getAttribute('data_target_id');"
    " if(!tid) return; var target=document.getElementById(tid); if(!target) return;"
    " target.value=(this.files && this.files.length)?this.files[0].name:'';}"
    " catch(err){console.warn('file->path bind',err)}});"
    "});"
    "</script>"
)
