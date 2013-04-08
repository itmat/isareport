"""Parse ISA-Tab structured metadata describing experimental data.

Works with ISA-Tab (http://isatab.sourceforge.net), which provides a structured
format for describing experimental metdata.

The entry point for the module is the parse function, which takes an ISA-Tab
directory (or investigator file) to parse. It returns a ISATabRecord object
which contains details about the investigation. This is top level information
like associated publications and contacts.

This record contains a list of associated studies (ISATabStudyRecord objects).
Each study contains a metadata attribute, which has the key/value pairs
associated with the study in the investigation file. It also contains other
high level data like publications, contacts, and details about the experimental
design.

The nodes attribute of each record captures the information from the Study file.
This is a dictionary, where the keys are sample names and the values are
NodeRecord objects. This collapses the study information on samples, and
contains the associated information of each sample as key/value pairs in the
metadata attribute.

Finally, each study contains a list of assays, as ISATabAssayRecord objects.
Similar to the study objects, these have a metadata attribute with key/value
information about the assay. They also have a dictionary of nodes with data from
the Assay file; in assays the keys are raw data files.

This is a biased representation of the Study and Assay files which focuses on
collapsing the data across the samples and raw data.
"""
from __future__ import with_statement

import os
import re
import csv
import glob
import collections
from oset import oset as OrderedSet


def parse(isatab_ref):
    """Entry point to parse an ISA-Tab directory.

    isatab_ref can point to a directory of ISA-Tab data, in which case we
    search for the investigator file, or be a reference to the high level
    investigation file.
    """
    if os.path.isdir(isatab_ref):
        fnames = glob.glob(os.path.join(isatab_ref, "i_*.txt")) + \
                 glob.glob(os.path.join(isatab_ref, "*.idf.txt"))
        assert len(fnames) == 1
        isatab_ref = fnames[0]
    assert os.path.exists(isatab_ref), "Did not find investigation file: %s" % isatab_ref
    i_parser = InvestigationParser()
    with open(isatab_ref, "rU") as in_handle:
        rec = i_parser.parse(in_handle)
    s_parser = StudyAssayParser(isatab_ref)
    rec = s_parser.parse(rec)
    return rec

class InvestigationParser:
    """Parse top level investigation files into ISATabRecord objects.
    """
    sections = {
            "ONTOLOGY SOURCE REFERENCE": "ontology_refs",
            "INVESTIGATION": "metadata",
            "INVESTIGATION PUBLICATIONS": "publications",
            "INVESTIGATION CONTACTS": "contacts",
            "STUDY DESIGN DESCRIPTORS": "design_descriptors",
            "STUDY PUBLICATIONS": "publications",
            "STUDY FACTORS": "factors",
            "STUDY ASSAYS" : "assays",
            "STUDY PROTOCOLS" : "protocols",
            "STUDY CONTACTS": "contacts"}

    def parse(self, in_handle):
        line_iter = self._line_iter(in_handle)
        # parse top level investigation details
        rec = Investigation()
        rec, _ = self._parse_region(rec, line_iter)
        # parse study information
        while 1:
            study = Study()
            study, had_info = self._parse_region(study, line_iter)
            if had_info:
                rec.studies.append(study)
            else:
                break
        # handle SDRF files for MAGE compliant ISATab
        if rec.metadata.has_key("SDRF File"):
            study = Study()
            study.metadata["Study File Name"] = rec.metadata["SDRF File"]
            rec.studies.append(study)
        return rec

    def _parse_region(self, rec, line_iter):
        """Parse a section of an ISA-Tab, assigning information to a supplied record.
        """
        had_info = False
        keyvals, section = self._parse_keyvals(line_iter)
        if keyvals:
            rec.metadata = keyvals[0]
        while section and section[0] != "STUDY":
            had_info = True
            keyvals, next_section = self._parse_keyvals(line_iter)
            attr_name = self.sections[section[0]]
            if attr_name == 'metadata':
                try:
                    keyvals = keyvals[0]
                except IndexError:
                    keyvals = {}
            setattr(rec, attr_name, keyvals)
            section = next_section
        return rec, had_info

    def _line_iter(self, in_handle):
        """Read tab delimited file, handling ISA-Tab special case headers.
        """
        reader = csv.reader(in_handle, dialect="excel-tab")
        for line in reader:
            if len(line) > 0 and line[0]:
                # check for section headers; all uppercase and a single value
                if line[0].upper() == line[0] and "".join(line[1:]) == "":
                    line = [line[0]]
                yield line

    def _parse_keyvals(self, line_iter):
        """Generate dictionary from key/value pairs.
        """
        out = None
        line = None
        for line in line_iter:
            if len(line) == 1 and line[0].upper() == line[0]:
                break
            else:
                # setup output dictionaries, trimming off blank columns
                if out is None:
                    while not line[-1]:
                        line = line[:-1]
                    out = [{} for _ in line[1:]]
                # add blank values if the line is stripped
                while len(line) < len(out) + 1:
                    line.append("")
                for i in range(len(out)):
                    out[i][line[0]] = line[i+1].strip()
                line = None
        return out, line

class StudyAssayParser:
    """Parse row oriented metadata associated with study and assay samples.

    This currently does not attempt to be complete, but rather to extract the
    most useful information (in my biased opinion) and represent it simply
    in the record objects.

    This is coded generally, so can be expanded to more cases. It is biased
    towards microarray and next-gen sequencing data.
    """
    _RE_NODES = re.compile(r'^(.+)\s(Name|File|REF)$')
    _RE_ATTRS = re.compile(r'([^\[]+)\[?([^\]]*)\]?')
    _RE_ATTR_QUALS = re.compile(r'(Unit|Term Accession Number|Term Source REF)')
    _GV_NODE_SHAPES = {'name' : 'rect', 'file': 'note', 'ref' : 'diamond' }

    def __init__(self, base_file):
        self._dir = os.path.dirname(base_file)

    def parse(self, rec):
        """Retrieve row data from files associated with the ISATabRecord.
        """
        final_studies = []
        for study_index, study in enumerate(rec.studies):
            source_data = self._parse_nodes(study.metadata["Study File Name"])
            if source_data:
                study.nodes = source_data
                final_assays = []
                for assay_index, assay in enumerate(study.assays):
                    cur_assay = Assay(assay)
                    assay_data = self._parse_nodes(assay["Study Assay File Name"])
                    cur_assay.nodes = assay_data
                    final_assays.append(cur_assay)
                study.assays = final_assays
                final_studies.append(study)
        rec.studies = final_studies
        return rec

    def _slug(self,name):
        return re.sub(r'[^0-9a-z.-_]','-',name.lower())

    def _collapse_rows(self,headers,reader):
        nodes = collections.OrderedDict()
        for row in reader:
            last_attr = None
            last_node = None
            for i in range(0,len(headers)):
                m = self._RE_ATTR_QUALS.match(headers[i])
                if m:
                    if len(row[i]) == 0: 
                        continue
                    # this is a qualifier for an attribute
                    # add it to the last attribute
                    last_node.metadata[last_attr][headers[i]] = row[i]
                else:
                    # not an attr qualifier
                    # test to see if a node
                    m = self._RE_NODES.match(headers[i])
                    if m:
                        # This is a node. Process it.
                        nid = self._slug(row[i])
                        # check to see if this is a REF
                        if m.group(2) == 'REF':
                            # it is. Force a new nid based on the parent
                            nid = last_node.nid + "-ref-" + nid
                        # check if this node exists
                        node = None
                        if not nodes.has_key(nid):
                            # this is a new node
                            nsubtype = self._slug(m.group(1))
                            ntype = self._slug(m.group(2))
                            label = row[i]
                            node = IsaNode(nid,ntype,nsubtype,label)
                            nodes[nid] = node
                        else: 
                            node = nodes[nid]
                        if last_node and last_node.nid != nid:
                            # print(last_node.nid, nid)
                            last_node.children.add(nid)
                            node.parents.add(last_node.nid)
                        last_node = node
                    else:
                        # This is an attribute. Add it to the last node.
                        m = self._RE_ATTRS.match(headers[i])
                        last_attr = attr_class = m.group(1)
                        if m.group(2) == '':
                            last_node.metadata[attr_class] = {'value': row[i]}
                        else:
                            if last_node.metadata.has_key(attr_class):
                                last_node.metadata[attr_class][m.group(2)] = row[i]
                            else:
                                last_node.metadata[attr_class] = {m.group(2) : row[i]}
        return nodes
    def _parse_nodes(self, fname):
        """Parse ISATab study or assay tab delimited files.
        """
        if not os.path.exists(os.path.join(self._dir, fname)):
            return None
        nodes = {}
        with open(os.path.join(self._dir, fname), "rU") as in_handle:
            reader = csv.reader(in_handle, dialect="excel-tab")
            header = reader.next()
            return self._collapse_rows(header,reader)
 

class Investigation:
    """Represent ISA-Tab Investigation metadata in structured format.

    High level key/value data.
      - metadata -- dictionary
      - ontology_refs -- list of dictionaries
      - contacts -- list of dictionaries
      - publications -- list of dictionaries

    Sub-elements:
      - studies: List of ISATabStudyRecord objects.
    """
    def __init__(self):
        self.metadata = {}
        self.ontology_refs = []
        self.publications = []
        self.contacts = []
        self.studies = []


class Study:
    """Represent a study within an ISA-Tab record.
    """
    def __init__(self):
        self.metadata = {}
        self.design_descriptors = []
        self.publications = []
        self.factors = []
        self.assays = []
        self.protocols = []
        self.contacts = []
        self.nodes = collections.OrderedDict()

class Assay:
    """Represent an assay within an ISA-Tab record.
    """

    def __init__(self, metadata={}):
        self.metadata = metadata
        self.nodes = collections.OrderedDict()


class IsaNode:
    """Represents a Node record (either from a ISATAB Study or Assay file).
    """
    types = {
        'name': 'entity',
        'file': 'file',
        'ref' : 'reference',
    }

    def __init__(self,nid,ntype,nsubtype,label):
        self.nid = nid
        self.ntype = self.types[ntype.lower()]
        self.nsubtype = nsubtype
        self.label = label
        self.parents = OrderedSet()
        self.children = OrderedSet()
        self.metadata = collections.defaultdict(collections.defaultdict)

    def __str__(self):
        return "Node: type=%s %s, nid='%s', label='%s'" % \
        (self.nsubtype, self.ntype, self.nid, self.label)