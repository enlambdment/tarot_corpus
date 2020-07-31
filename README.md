# tarot_corpus

A project to extract a corpus of tarot guides, with a minimum of extraneous material, for further use elsewhere (research, NLP, _etc._) 

## Set-up

```
git clone https://github.com/enlambdment/tarot_corpus
cd tarot_corpus
python3 -m venv env
source env/bin/activate
pip3 install -r requirements.txt
```

The directory `data/sacredtext_tarot_guides/` already includes corpus text & HTML tables extracted for your convenience. If you want to repeat the extraction for yourself, delete this folder's contents, then follow these steps:

```
python3 -i tarot_text_scrape.py
>>> make_corpus()
``` 

The directory should have all 10 `.txt` files restored (2 for each of 5 texts included in the corpus.)

Once you're finished:

```
>>> quit()
deactivate
```

## Note for `nltk` use

`nltk` is an additional library not in `requirements.txt`. Launch the first series of commands, to clone / activate virtual environment / install libraries, in 'Set-up section'. Then:

```
pip3 install nltk
```

You can continue to run `tarot_text_scrape.py` script and `make_corpus()` method. Then:

```
>>> from nltk.corpus import PlaintextCorpusReader
>>> corpus_root = './data/sacredtext_tarot_guides'
>>> wordlists = PlaintextCorpusReader(corpus_root, '^((?!_tbls).)*.txt')
```

As of this writing (_7/31/2020_) the negative lookahead expression is needed in order to exclude the '\_tbls.txt' files, which are unprocessed HTML.

```
>>> wordlists.fileids()
['gbt.txt', 'mathers.txt', 'pkt.txt', 'sot.txt', 'tob.txt']
```

## Background

The _Sacred Texts_ online archive includes a section on [tarot](https://sacred-texts.com/tarot/), with public-domain texts edited and typeset to HTML by John Bruno Hare. Tarot originally was a deck of playing cards whose use dates back to the mid-15th century in certain parts of Europe: today, tarot most commonly refers both to this deck (which has evolved into many non-standard forms in the 21st century) and the practices of divination, fortune-telling, _etc._ which have developed based upon that deck, from the late 18th century onward. 

Tarot, and adjacent practices such as astrology, are enjoying [something](https://www.newyorker.com/magazine/2019/10/28/astrology-in-the-age-of-uncertainty) [of](https://www.nytimes.com/2019/08/28/style/therapy-psychology-astrology-tarot-ayahuasca.html) [a](https://www.thecut.com/article/tarot-cards.html) [resurgence](https://www.wired.com/gallery/best-tarot-card-apps/) as of this writing. The literature of the tarot comprises a rich universe of associations relating the cards which make up the deck, the images which decorate them, and the archetypal personalities, situations and events which they represent. Certain interpretive systems of the tarot go further, positing sophisticated and highly abstract numerical, alphabetical and other associations for the cards.

For scholars of the tarot's history, individuals in the digital arts and humanities, and practitioners adapting tarot for themselves and others, a corpus of tarot guides parsed and edited into a plaintext format is highly desirable, for immediate ease of storage and use as well as for utilizing with NLP software in other environments.

## Objectives

Out of the public-domain texts made available on the _Sacred Texts_ tarot page, I selected five for consideration and skimmed these texts' front pages and subsections. The idea was to inspect the HTML of main-text vs. extraneous elements (_e.g._ notes, paragraph numbers, styling elements for webpages, etc.), with an eye towards identifying what properties (tag types, tag attributes, positioning of tags on the page relative to other elements _etc._) could reliably contrast tags containing main text versus those which do not. Having done so, `tarot_text_scrape.py` was written to implement logic for selecting tags, then extracting text and tabular information as appropriate, based upon an understanding of those contrasting properties.

## Design considerations

The front-page website url's (which each present a hyperlinked table of contents) for the chosen public-domain texts are included in `tarot_front_pages.txt` so that they may be separately modified, in case the list of chosen texts were to be changed in the future (without being hard-coded into the Python script for scraping the texts themselves.) 

With these front-page url's in hand, each of them can be requested using `requests` library, then the response parsed using `BeautifulSoup` and the hierarchically structured HTML output examined in order to locate the subsection urls. 

Because the root path for any given subsection is understood in the context of the front-page website, that page's HTML links internally to subsections by specifying the _suffix_, _e.g._ `gbt04.htm` for the _Lesser Arcana_ section in _General Book of the Tarot_ which is a subsection of `https://www.sacred-texts.com/tarot/gbt`. This means that the url suffixes for each subsection must be located in the front-page response, then the full subsection urls reassembled out of the root path and suffixes. 

However, locating these url suffixes is not as simple as identifying any hyperlink tags (`a` elements) and then using those tags' `href` attributes, because the front page includes tags which implement navigation elsewhere within the _Sacred Texts_ website, or to other websites. The Python standard library includes `re` for specifying regular-expression (regex) patterns and compiling these into objects usable for string searching & matching, and I used this library to specify selection criteria for `href` attributes specifying valid url suffixes for the text's subsections.

With the subsection suffixes selected & the full subsection url's reassembled out of these, what remains is to build up the entire text by taking each subsection url at a time & extracting text from all the relevant tags. The following observations guided the implementation of the scraping script:

- Every subsection's page begins with a head element including website navigation elements, _etc._, then is followed by a heading as an `h[n]` tag, with the numeral `[n]` varying according to level in the overall text;
- In addition to typesetting the main text in standard fashion, within paragraphs (`p` tags), 
	- each subsection may include certain portions of the text outside of such tags; 
	- or, because of discrepancies between the page's own mark-up versus the HTML formation rules which the parser in use (`html.parser`, `html5lib` _etc._) expects, properly marked-up text in the response may land outside of their original tags in the parsing output.
- Every page also includes certain navigation elements at the foot of the page; these take the form of  `center` elements containing hyperlinks which point elsewhere in the text.
- As well as strings suitable for extraction to form the corpus text, 
	- other strings are specially formatted in `font` elements, to give them colors differing from the main text; these usually stand for page & paragraph numbering for cross-referencing the digital text with its original printed form.
	- However, some of these `font` elements contain attribution material which name the redactor who adapted these texts into their digital form: these elements must _not_ be excluded from the text, and must have their text extracted into the final corpus text.
- Finally, some of the elements contain tabular information, in `table` tags, which can often have their text extracted for use in the corpus but may also be of interest in their original tabular representation (for separate future processing using structures such as lists, dictionaries _etc._)

These design considerations called for an approach where, broadly speaking, every element is viewed from two perspectives: for their primary interest as containing possible corpus text, and for their tabular content (if any.)

When processing a parsed subsection, the first thing is to locate the first heading present. The parsed object is hierarchical in structure, as previously mentioned; the `BeautifulSoup` method `find('x')` will locate the first `x` tag present in the parse, regardless of its layer in the overall structure. Because the first heading tag may be of arbitrary importance, we have to match `h` followed by an arbitrary single-digit numeral & an `re` pattern is used for this task as well.

From there, every sibling of this first element is looked at, one at a time & in the order in which it appears. Again due to the essentially nested nature of HTML tags, the text of interest in each such sibling may exist directly in that element, _or_ among its descendants. The `BeautifulSoup` method `find_all(...)` is used to identify _all_ elements within a tag that satisfy the condition(s) provided as argument(s): see [here](https://www.crummy.com/software/BeautifulSoup/bs4/doc/#searching-the-tree) for more information on its use. Because we simply are interested in examining all descendants, we pass the trivial condition to this method, _i.e._ `find_all(True)`. Then each tag can be tested for its name, attributes, _etc._ and dealt with accordingly.

Tables can be copied using the `BeautifulSoup` implementation of the `copy` method for an element, which creates a copy outside of the overall parse context in which it originally appeared. By contrast, tags whose text are not of interest for the corpus are simply destroyed in-place during the recursive examination of their parent tag. (A regular-expression pattern search makes sure that such text doesn't include redactor attributions, before destruction.) With these steps taken care of, `get_text` method (or simple `str()` casting, for HTML tables and `BeautifulSoup` `NavigableString` elements) is used to build up the subsection's string to include in the overall corpus files.




