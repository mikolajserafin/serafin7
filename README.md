# Correspondence of Mikołaj Serafin

First published as *Korespondencja żupnika krakowskiego Mikołaja Serafina z lat 1437-1459* 
by __Anna Skolimowska, Waldemar Bukowski, Tomasz Płóciennik__ (eds.), *Societas Vistulana*, Kraków, 2006

## data

Correspondence data is organized in two collections, nested under `data`. Transcriptions of letters are stored in `data/letters` collection as separate TEI documents, one per each letter, while all prosopographical information is stored in `data/auxiliary/authorityLists.xml`.

## encoding guidelines

### translation

Each letter transcription is accompanied by parallel Polish translation. Both are represented by `text` elements and wrapped together as a `group`

```xml
<text>
  <group>
    <text type="source" xml:id="s" xml:lang="la"/>
    ...
    </text>
    <text type="translation" xml:id="t" xml:lang="pl"/>
    ...
    </text>
  </group>
</text>
```

Alignment is achieved through `seg` elements marking translation equivalents with `xml:id` attributes following a nesting numbering pattern with text id as a prefix and `.` as a separator. Thus if original source transcription is held in `text` element with `xml:id="s"`, one of translation segments may be given an `xml:id="s.1.4.1"`, corresponding translation in `text xml:id="t"` would have `xml:id="t.1.4.1"`

### conjectures

editor's conjectures are marked with `<supplied>` element

### unclear passages

unclear passages represented in print with `<?>` should be encoded with `<unclear>`, e.g. `misi[?]` is to be encoded as `<unclear>misi</unclear>`

### missing passages

completely illegible or missing passages visualized in print as `[...]` or similar should be encoded with `<gap>` element. Extent of the missing text can be given with `quantity` and `unit` attributes, e.g. `<gap quantity="4" unit="chars"/>`

### abbreviations

abbreviations are given in expanded version with `<expan>` and `<ex>` elements, e.g. `<expan>N<ex>obilitatem</ex></expan>`

### erroneous passages

errorneous passages represented with `<!>` in print are encoded with `<sic>`, e.g. <sic>succamararii</sic>

### dates

date's in the text should be marked up with regularized value in `when` and `when-custom` attributes, e.g. `Ascenssionis Domini [10 V]` should be represented as `<date when="1437-05-10" when-custom="10 V">Ascenssionis Domini</date>`









