# Data card (Week 3)

Crawled 28 Oct 2026 (`fetched_at` on every record). Rebuild with `python src/ingest.py`.

| Source | Domain | Pages | Words |
|---|---|---|---|
| GOV.UK | schools | 12 | 8,087 |
| GOV.UK | housing | 12 | 21,398 |
| GOV.UK | health | 2 | 1,959 |
| NHS.uk | health | 12 | 7,570 |
| **Total** | | **38** | **39,014** |

After chunking: 432 chunks (health 101, housing 237, schools 94), median 78 words.

Page formats: GOV.UK guide 15, local_transaction 6, answer 3, transaction 1, detailed_guide 1; NHS article 12.

## Licence and reuse
- **GOV.UK:** Crown copyright, Open Government Licence v3.0. Attribute and link.
- **NHS.uk:** the site's terms release content under the Open Government Licence, with extra conditions:
  attribute each item with a link to the source page, and either refresh copied content regularly or
  show users the date it was copied. The assistant therefore shows the source link and fetch date with
  every citation. (https://www.nhs.uk/our-policies/terms-and-conditions/)
- Crawling: the NHS robots.txt does not disallow the pages used. Requests are spaced by 0.5 s.

## Known issues
1. **Publisher dates do not show content currency.** GOV.UK's `public_updated_at` is 2015-10-23 for
   *Private renting for tenants: evictions in England*, yet the page text already describes the
   1 May 2026 Renters' Rights Act changes. Store `fetched_at` and treat it as the reference date.
2. **Law change on 1 May 2026.** Section 21 "no fault" evictions ended in England on 1 May 2026.
   Any answer from an older snapshot or from an ungrounded LLM may still describe section 21 as available.
   This is a strong test case for grounded vs ungrounded comparison.
3. **Council hand-off pages.** Six GOV.UK pages (e.g. *Apply for a primary school place*) are
   local_transaction pages of 40-120 words that send users to their council. They hold no deadlines or
   local rules; the national dates live on *School admissions*.
4. **Mixed nations.** Some GOV.UK pages include sections for Scotland, Wales and Northern Ireland.
   These must be tagged and filtered (week 5).
5. **Imbalance.** Housing has about twice the words of each other domain; results are reported per domain.
