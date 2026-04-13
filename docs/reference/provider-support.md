# Provider Support

Scriptoria supports a mixed set of direct-resolution providers and search-capable providers. Support does not mean that every provider behaves the same way. Some are strongest when you already have a stable identifier or record URL, while others support broad free-text discovery directly inside the product.

## Supported Providers

- Vaticana
- Gallica
- Institut de France
- Bodleian
- Heidelberg
- Cambridge
- e-codices
- Harvard
- Library of Congress
- Internet Archive
- Generic direct IIIF manifest URL

## Support Model

Provider support is split across:

- direct resolution of URLs and supported identifiers;
- free-text search adapters where stable provider behavior exists;
- provider-specific network policy when upstream services require stricter rate limiting or headers.

## Provider Matrix

| Provider | Best input type | Search behavior | What to paste/search first |
| --- | --- | --- | --- |
| Vaticana | Shelfmark or manifest URL | `fallback` | Shelfmark such as `Urb.lat.1779`, or a direct manifest URL |
| Gallica | ARK, record URL, or text query | `search_first` | ARK ID, Gallica URL, or free-text query; optional material filter |
| Institut de France | Numeric ID, record URL, or text query | `fallback` | Numeric ID such as `17837`, viewer URL, or text query |
| Bodleian | UUID or record URL | `direct` with search support | Digital Bodleian UUID or item URL |
| Heidelberg | Record ID or item URL | `fallback` | Catalog ID or URL; free text is less reliable |
| Cambridge | Shelfmark or item URL | `fallback` | Shelfmark such as `MS-ADD-03996` or CUDL URL |
| e-codices | Compound identifier or URL | `direct` with search support | ID such as `csg-0001` or e-codices URL |
| Harvard | DRS-based item URL | `fallback` | Harvard IIIF/HOLLIS URL carrying the DRS identifier |
| Library of Congress | Item URL | `fallback` | `loc.gov/item/...` URL |
| Internet Archive | Item URL or text query | `search_first` | `archive.org/details/...` URL or free-text query |
| Other / Generic | Direct IIIF manifest URL | `direct` | Exact manifest URL only |

## Search Modes Explained

Scriptoria uses three discovery modes internally.

- `direct`: the provider is mainly treated as a resolver. Explicit identifiers and URLs are the expected input.
- `fallback`: Scriptoria first tries to resolve explicit input and can fall back to provider search behavior.
- `search_first`: the product treats free-text search as a first-class workflow for that provider.

This distinction is operational, not editorial. It explains why one provider feels friendly to exploratory discovery while another is much more reliable when you already know the exact record you want.

## Per-Provider Notes

### Vaticana

- Strongest with shelfmarks and explicit manuscript references.
- Free-text behavior exists, but the best practical input is still a shelfmark-like reference.
- Good examples: `Urb.lat.1779`, a direct Vaticana item URL, or a direct manifest URL.

### Gallica

- One of the best discovery-first providers in the current product.
- Supports free-text search and provider-specific filtering.
- Good examples: ARK IDs, Gallica item URLs, text queries, and manuscript-vs-print filtering.

### Institut de France

- Supports search, but exact numeric IDs and viewer URLs remain the most reliable input.
- Useful when you know the record but still want product-side search fallback.

### Bodleian

- Best results come from a direct UUID or Digital Bodleian URL.
- Better treated as an explicit-resolution provider than as a broad keyword search surface.

### Heidelberg

- Free-text search can be variable.
- The practical recommendation is to use an explicit catalog ID or record URL whenever possible.
- If free-text discovery is needed, browser-assisted search may still be the fastest path.

### Cambridge

- Similar to Heidelberg in practice.
- Strongest with shelfmarks and direct CUDL record URLs.
- Product-side free-text support is present, but record-level references are usually more dependable.

### e-codices

- Strong with explicit compound identifiers.
- Good examples: `csg-0001` and direct e-codices record URLs.

### Harvard

- Best treated as a URL-driven provider.
- Use item URLs carrying the DRS identifier whenever possible.

### Library of Congress

- Best treated as a record-URL provider.
- Use the public `loc.gov/item/...` URL as the starting reference.

### Internet Archive

- Supports discovery-first workflows reasonably well.
- Good with either a direct item URL or a text query.

### Generic Direct Manifest

- Use this path only when you already have a valid IIIF manifest URL and the provider is not covered by a dedicated resolver.

## Operational Caution

Provider support is not only about parsing. Some upstream services are fragile, rate-limited, or inconsistent enough that they affect retries, throttling, and discovery UX. A provider can be officially supported and still work best with explicit record references instead of generic keyword search.

## Related Docs

- [Getting Started](../intro/getting-started.md)
- [Discovery And Library](../guides/discovery-and-library.md)
- [Discovery And Provider Model](../explanation/discovery-provider-model.md)
- [HTTP Client Notes](../HTTP_CLIENT.md)
- [Test Suite Guide](../project/testing-guide.md)
