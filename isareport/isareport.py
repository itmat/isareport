# External imports
import argparse
import haml
import mako.template
import pygraphviz
import os
import logging
import tempfile
from bcbio import isatab
import yaml
from slug import slug

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
        logging.setLevel(logging.INFO)
    if args.debug:
        logging.setLevel(logging.DEBUG)

def sanitize_name(n):
    return slug(unicode(n))

def generate_study_graph(study):
    g = pygraphviz.AGraph(directed=True,rankdir='LR')
    # generate_investigation(g,investigation)
    sid = sanitize_name(study.metadata['Study Identifier'])
    for k in study.nodes.keys():
        n = study.nodes[k]
        nid = sanitize_name(sid + " - " + k)
        g.add_node(nid,label=k,URL="#g-" + nid)
        for src in n.metadata['Source Name']:
            srcid = sanitize_name(sid + " - " + src)
            g.add_node(srcid,label=src,URL="#g-" + srcid)
            g.add_edge(srcid,nid)
    return g

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
    investigation = isatab.parse(args.isatab_metadata_directory)

    # setup the report templates and output
    template = mako.template.Template(
        filename=os.path.join('isareport','static','templates','report.html.haml'),
        preprocessor=haml.preprocessor
    )

    # get the graph structure of the Investigation
    inv_graph = generate_study_graph(investigation.studies[0])
    # write out the SVG
    svg = tempfile.NamedTemporaryFile()
    inv_graph.draw(svg.name,format='svg',prog='dot')
    context = {"svg_file": svg.name,"investigation": investigation}

    args.output.write(template.render(**context))
    svg.close()


def main(): 
    '''Run ISA-Report'''
    args = get_arguments()
    setup_logging(args)
    logging.info("Running Report Generation")
    logging.debug('ARGS: ' + str(args))
    run_report(args)

if __name__ == '__main__':
    main()
