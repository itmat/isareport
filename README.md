#ISA-Report
-----------

Let's just go on the record that we feel that ISA-TAB is a terrible "standard" format. But the community has spoken, so better to go with the flow and write some tools to make the format more useful for everyone. Enter ISA-Report.

ISA-Report is a tool, written in python, to create interactive and useful HTML5 reports from ISA-TAB experimental annotation files.

The report consists of an interactive graph visualization of the Assays, Samples, Protocols, Data Files, etc., described in the ISA-TAB files, along with readable reports of the annotation laid out in a sensible format. Visualization comes courtesy of the excellent [D3.js](http://d3js.org) library. 

Once released, you should be able to simple do the following to install:

```python
pip install isa-graph
```

Until then, though, you will need to download this repo and install like so:

```bash
git clone https://github.com/itmat/isareport.git
cd isareport
python setup.py install 
```

## USAGE

```bash
cd path/to/directory/containing/isatab/files
isareport my.awesome.isatab.file.isa
```
