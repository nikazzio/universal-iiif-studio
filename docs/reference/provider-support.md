# Provider Support

Scriptoria currently supports a mixed set of direct-resolution providers and search-capable providers.

## Providers Commonly Mentioned In The Product

- Vaticana
- Gallica
- Bodleian
- Cambridge
- Heidelberg
- Harvard
- Library of Congress
- Archive.org
- e-codices
- Institut de France

## Support Model

Provider support is split across:

- direct resolution of URLs and supported identifiers;
- free-text search adapters where stable provider behavior exists;
- provider-specific network policy when upstream services require stricter rate limiting or headers.

## Operational Caution

Provider support is not only about parsing. Some upstream services are fragile, rate-limited, or inconsistent enough that they affect retries, throttling, and discovery UX.

## Related Docs

- [Discovery And Provider Model](../explanation/discovery-provider-model.md)
- [HTTP Client Notes](../HTTP_CLIENT.md)
- [Test Suite Guide](../project/testing-guide.md)
