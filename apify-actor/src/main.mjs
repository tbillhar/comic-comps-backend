import { Actor, log } from "apify";
import { PlaywrightCrawler } from "crawlee";

await Actor.init();

const input = await Actor.getInput() ?? {};

const query = String(input.query ?? "").trim();
const maxResults = clampInteger(input.maxResults, 50, 1, 200);
const ebaySite = String(input.ebaySite ?? "ebay.com").trim() || "ebay.com";
const currency = String(input.currency ?? "USD").trim() || "USD";
const useApifyProxy = input.useApifyProxy !== false;
const sort = String(input.sort ?? "endedRecently").trim() || "endedRecently";

if (!query) {
    throw new Error("Input field 'query' is required.");
}

const state = {
    pushed: 0,
    seenUrls: new Set(),
};

const proxyConfiguration = useApifyProxy
    ? await Actor.createProxyConfiguration({ useApifyProxy: true })
    : undefined;

const crawler = new PlaywrightCrawler({
    maxRequestsPerCrawl: 25,
    headless: true,
    requestHandlerTimeoutSecs: 120,
    proxyConfiguration,
    async requestHandler({ page, request, enqueueLinks, log: requestLog }) {
        await page.waitForLoadState("domcontentloaded");
        await page.waitForTimeout(2000);
        await handleConsent(page);
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(1500);

        const pageDiagnostics = await page.evaluate(() => {
            const normalizeWhitespace = (value) => value.replace(/\s+/g, " ").trim();
            const cards = collectResultCards();
            const bodyText = normalizeWhitespace(document.body?.innerText ?? "");
            const sampleLinkTexts = Array.from(document.querySelectorAll("a[href*='/itm/']"))
                .slice(0, 5)
                .map((node) => normalizeWhitespace(node.textContent ?? ""))
                .filter(Boolean);
            const sampleCardHtml = cards[0]?.outerHTML?.slice(0, 1000) ?? null;

            return {
                title: document.title,
                href: location.href,
                cardCount: cards.length,
                bodySnippet: bodyText.slice(0, 500),
                sampleLinkTexts,
                sampleCardHtml,
            };

            function collectResultCards() {
                const directCards = Array.from(
                    document.querySelectorAll(
                        ".srp-results .s-item, .srp-river-results .s-item, li.s-item, li.srp-results__item, .srp-river-results > li",
                    ),
                );
                if (directCards.length > 0) {
                    return uniqueElements(directCards);
                }

                const linkCards = Array.from(document.querySelectorAll("a[href*='/itm/']"))
                    .map((link) => link.closest("li, article, div"))
                    .filter(Boolean);

                return uniqueElements(linkCards);
            }

            function uniqueElements(elements) {
                return Array.from(new Set(elements));
            }
        });

        const extractedRows = await page.evaluate(() => {
            const cards = collectResultCards();

            return cards.map((card) => {
                const cardText = normalizeWhitespace(card.textContent ?? "");
                const title = normalizeWhitespace(
                    textFrom(card, [
                        ".s-item__title",
                        "[data-testid='x-refine__rightPanel--srp-results'] .s-item__title",
                        "[role='heading']",
                    ]),
                );

                const url =
                    card.querySelector(".s-item__link")?.href?.trim() ??
                    card.querySelector("a[href*='/itm/']")?.href?.trim() ??
                    null;

                const priceCandidates = Array.from(card.querySelectorAll(".s-item__price"))
                    .map((node) => normalizeWhitespace(node.textContent ?? ""))
                    .filter(Boolean);

                const shippingCandidates = Array.from(
                    card.querySelectorAll(".s-item__shipping, .s-item__logisticsCost"),
                )
                    .map((node) => normalizeWhitespace(node.textContent ?? ""))
                    .filter(Boolean);

                const dateCandidates = Array.from(
                    card.querySelectorAll(
                        ".s-item__caption--signal, .s-item__title--tagblock, .POSITIVE, .s-item__dynamic",
                    ),
                )
                    .map((node) => normalizeWhitespace(node.textContent ?? ""))
                    .filter(Boolean);

                return {
                    title,
                    url,
                    rawPriceText: chooseDisplayedPrice(priceCandidates),
                    rawShippingText: shippingCandidates[0] ?? null,
                    rawDateText: chooseSoldDate(dateCandidates, cardText),
                    rawCardText: cardText,
                };
            });

            function collectResultCards() {
                const directCards = Array.from(
                    document.querySelectorAll(
                        ".srp-results .s-item, .srp-river-results .s-item, li.s-item, li.srp-results__item, .srp-river-results > li",
                    ),
                );
                if (directCards.length > 0) {
                    return uniqueElements(directCards);
                }

                const linkCards = Array.from(document.querySelectorAll("a[href*='/itm/']"))
                    .map((link) => link.closest("li, article, div"))
                    .filter(Boolean);

                return uniqueElements(linkCards);
            }

            function textFrom(root, selectors) {
                for (const selector of selectors) {
                    const value = root.querySelector(selector)?.textContent?.trim();
                    if (value) {
                        return value;
                    }
                }
                return "";
            }

            function normalizeWhitespace(value) {
                return value.replace(/\s+/g, " ").trim();
            }

            function uniqueElements(elements) {
                return Array.from(new Set(elements));
            }

            function chooseDisplayedPrice(candidates) {
                const filtered = candidates.filter((candidate) => {
                    const lowered = candidate.toLowerCase();
                    return !lowered.includes("shop on ebay");
                });

                for (const candidate of filtered) {
                    if (extractAmount(candidate) !== null) {
                        return candidate;
                    }
                }

                return filtered[0] ?? null;
            }

            function chooseSoldDate(candidates, cardText) {
                for (const candidate of candidates) {
                    if (containsSaleDate(candidate)) {
                        return candidate;
                    }
                }

                if (containsSaleDate(cardText)) {
                    return extractSaleDateSegment(cardText);
                }

                return null;
            }

            function containsSaleDate(text) {
                return (
                    /sold\s+[a-z]{3}\s+\d{1,2},\s+\d{4}/i.test(text) ||
                    /\b[a-z]{3}\s+\d{1,2},\s+\d{4}\b/i.test(text)
                );
            }

            function extractSaleDateSegment(text) {
                const soldMatch = text.match(/sold\s+([a-z]{3}\s+\d{1,2},\s+\d{4})/i);
                if (soldMatch) {
                    return `Sold ${soldMatch[1]}`;
                }

                const plainMatch = text.match(/\b([a-z]{3}\s+\d{1,2},\s+\d{4})\b/i);
                if (plainMatch) {
                    return plainMatch[1];
                }

                return null;
            }

            function extractAmount(text) {
                const match = text.match(/([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})|[0-9]+(?:\.[0-9]{2}))/);
                return match ? match[1] : null;
            }
        });

        requestLog.info(`Extracted ${extractedRows.length} candidate cards from ${request.url}`, pageDiagnostics);

        if (pageDiagnostics.cardCount === 0) {
            requestLog.warning("No eBay result cards detected on page.", pageDiagnostics);
        }

        for (const row of extractedRows) {
            if (state.pushed >= maxResults) {
                break;
            }

            const normalizedRow = normalizeRow(row, currency);
            if (!normalizedRow) {
                continue;
            }
            if (state.seenUrls.has(normalizedRow.url)) {
                continue;
            }

            state.seenUrls.add(normalizedRow.url);
            state.pushed += 1;
            await Actor.pushData(normalizedRow);
        }

        const nextPageUrl = await page.evaluate(() => {
            const nextLink =
                document.querySelector("a[aria-label='Go to next search page']") ??
                document.querySelector("a.pagination__next");
            return nextLink?.href?.trim() ?? null;
        });

        if (nextPageUrl && state.pushed < maxResults) {
            requestLog.info(`Queueing next page: ${nextPageUrl}`);
            await enqueueLinks({
                urls: [nextPageUrl],
                forefront: false,
            });
        }
    },
});

const startUrl = buildSoldSearchUrl({ query, ebaySite, sort });
log.info(`Starting eBay sold/completed scrape for query '${query}'`, { startUrl, maxResults });

await crawler.run([{ url: startUrl, uniqueKey: startUrl }]);

await Actor.exit();

async function handleConsent(page) {
    const consentSelectors = [
        "button#gdpr-banner-accept",
        "button[data-testid='gdpr-banner-accept']",
        "button[aria-label='Accept']",
        "button:has-text('Accept all')",
        "button:has-text('Accept')",
        "input[type='submit'][value='Accept']",
    ];

    for (const selector of consentSelectors) {
        try {
            const locator = page.locator(selector).first();
            if (await locator.isVisible({ timeout: 1000 })) {
                await locator.click({ timeout: 2000 });
                await page.waitForTimeout(1000);
                return;
            }
        } catch {
            // Ignore selector-specific failures and continue probing.
        }
    }
}

function buildSoldSearchUrl({ query, ebaySite, sort }) {
    const url = new URL(`https://www.${ebaySite}/sch/i.html`);
    url.searchParams.set("_nkw", query);
    url.searchParams.set("LH_Sold", "1");
    url.searchParams.set("LH_Complete", "1");
    url.searchParams.set("rt", "nc");
    url.searchParams.set("_ipg", "240");

    if (sort === "endedRecently") {
        url.searchParams.set("_sop", "13");
    }

    return url.toString();
}

function normalizeRow(row, currency) {
    const title = cleanString(row.title);
    const url = cleanString(row.url);
    const rawPriceText = cleanString(row.rawPriceText);
    const rawShippingText = cleanString(row.rawShippingText);
    const rawDateText = cleanString(row.rawDateText);
    const rawCardText = cleanString(row.rawCardText);

    if (!title || !url || !rawPriceText || !rawDateText) {
        return null;
    }

    const price = extractAmount(rawPriceText);
    const shippingPrice = extractAmount(rawShippingText);
    const saleDate = parseSoldDate(rawDateText);

    if (!price || !saleDate) {
        return null;
    }

    const totalPrice = shippingPrice ? formatAmount(Number(price) + Number(shippingPrice)) : price;
    const itemId = extractItemId(url) ?? url;

    return {
        id: itemId,
        title,
        url,
        saleDate,
        price,
        shippingPrice,
        totalPrice,
        currency,
        rawPriceText,
        rawShippingText,
        rawDateText,
        rawCardText,
    };
}

function cleanString(value) {
    if (typeof value !== "string") {
        return null;
    }

    const normalized = value.replace(/\s+/g, " ").trim();
    return normalized || null;
}

function extractAmount(text) {
    if (!text) {
        return null;
    }

    const match = text.match(/([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})|[0-9]+(?:\.[0-9]{2}))/);
    if (!match) {
        return null;
    }

    return match[1].replace(/,/g, "");
}

function parseSoldDate(text) {
    const match = text.match(/sold\s+([a-z]{3}\s+\d{1,2},\s+\d{4})/i);
    let dateText = match ? match[1] : null;

    if (!dateText) {
        const plainMatch = text.match(/\b([a-z]{3}\s+\d{1,2},\s+\d{4})\b/i);
        dateText = plainMatch ? plainMatch[1] : null;
    }

    if (!dateText) {
        return null;
    }

    const parsedDate = new Date(`${dateText} 00:00:00 UTC`);
    if (Number.isNaN(parsedDate.getTime())) {
        return null;
    }

    return parsedDate.toISOString();
}

function extractItemId(url) {
    const match = url.match(/\/itm\/([0-9]+)/);
    return match ? match[1] : null;
}

function formatAmount(value) {
    return value.toFixed(2);
}

function clampInteger(value, fallback, min, max) {
    const numericValue = Number.parseInt(String(value ?? fallback), 10);
    if (Number.isNaN(numericValue)) {
        return fallback;
    }
    return Math.min(max, Math.max(min, numericValue));
}
