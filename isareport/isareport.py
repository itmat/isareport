# External imports
import argparse
import haml
import mako.template
import pygraphviz as gv
import os
import re
import logging
import tempfile
import parser
import yaml

GVSHAPES = {
    'file': "rect", 
    'entity': 'ellipse',
    'reference': 'diamond'
}
def slug(name):
    return re.sub(r'[^0-9a-z.-_]','-',name.lower())

def get_arguments():
    args = argparse.ArgumentParser()
    args.add_argument(
        "isatab_metadata_directory",
        type=str,
        help="The path to the ISA-TAB metadata directory."
    )
    args.add_argument(
        "--output","-o",
        default="isareport.html",
        type=argparse.FileType('w'),
        help="The path to the output HTML report file."
    )
    args.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Be verbose"
    )
    args.add_argument(
        '--debug', '-d',
        action='store_true',
        help="Print debugging information"
    )
    return args.parse_args()

def setup_logging(args):
    logging.basicConfig(level=logging.ERROR,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

def generate_subgraph(name,nodes,g):
    gg = g.subgraph(name="cluster-" + slug(name))
    for node in nodes:
        shape = GVSHAPES[node.ntype]
        # check to see of a REF
        gg.add_node(node.nid,label=node.label,URL="#g-" + node.nid, shape=shape)
    # add in the edges
    for node in nodes:
        for c in node.children:
            gg.add_edge(node.nid, c)
    return gg

def run_report(args):
    # parse the ISA-TAB file
    if not os.path.exists(args.isatab_metadata_directory):
        logging.error("ISA-TAB metadata directory does not exists: " +
            args.isatab_metadata_directory)
        raise BaseException("Directory does not exists" + args.isatab_metadata_directory)
        exit()
    if not os.path.isdir(args.isatab_metadata_directory):
        logging.error("ISA-TAB metadata directory does not exists: " +
            args.isatab_metadata_directory)
        raise BaseException("Not a directory" + args.isatab_metadata_directory)
        exit()
    investigation = parser.parse(args.isatab_metadata_directory)

    # setup the report templates and output
    template = mako.template.Template(
        filename=os.path.join('isareport','static','templates','report.html.haml'),
        preprocessor=haml.preprocessor
    )

    # get the graph structure of the Investigation
    study_graphs = {}
    ### TO-DO: Clean up the mess below. Need to figure out a good way for multiple SVG files.
    for study in investigation.studies:
        g = gv.AGraph(directed=True,rankdir='LR',name=slug(investigation.metadata['Investigation Identifier']))
        for study in investigation.studies:
            generate_subgraph(study.metadata['Study Identifier'],study.nodes.values(),g)
            # add assays
            for assay in study.assays:
                aname = assay.metadata['Study Assay File Name']
                generate_subgraph(aname,assay.nodes.values(),g)
            # write out the SVG
        sfbasename  = slug(study.metadata['Study Identifier']) 
        svg = os.path.join(tempfile.gettempdir(), sfbasename + '.svg')
        g.draw(svg,format='svg',prog='dot')
        study_graphs[study.metadata['Study Identifier']] = {'f': svg, "g": g} 
        if args.debug:
            tmpf  = open(sfbasename + '.dot' ,'w')
            tmpf.write(g.to_string())
            tmpf.close()
    context = {"svg_file": [study_graphs[x]['f'] for x in study_graphs.keys()] ,"investigation": investigation}
    args.output.write(template.render(**context))

def main():
    '''Run ISA-Report'''
    args = get_arguments()
    setup_logging(args)
    logging.info("Running Report Generation")
    logging.debug('ARGS: ' + str(args))
    run_report(args)

if __name__ == '__main__':
    main()
