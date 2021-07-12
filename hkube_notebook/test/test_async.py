from hkube_notebook.pipeline.exec import PipelineExecutor
from hkube_notebook.pipeline.create import PipelineBuilder
from hkube_notebook.pipeline.tracker import TrackerType
from hkube_notebook.config import config

input = {
    "text": ["In mathematics and computer science, a directed acyclic graph ",
    "(DAG (About this sound listen)), is a finite directed graph with",
    " no directed cycles. That is, it consists of finitely many vertices and",
    "edges, with each edge directed from one vertex to another, ",
    "such that there is no way to start at any vertex v and follow",
    "a consistently-directed sequence of edges that eventually ",
    "loops back to v again. Equivalently, a DAG is a directed graph",
    "that has a topological ordering, a sequence of the vertices ",
    "such that every edge is directed from earlier to later in the sequence.",
    "DAGs can model many different kinds of information. ",
    "A spreadsheet can be modeled as a DAG, with a vertex ",
    "for each cell and an edge whenever the formula in one ",
    "cell uses the value from another; a topological ordering of this ",
    "DAG can be used to update all cell values when the spreadsheet is ",
    "changed. Similarly, topological orderings of DAGs can be used to order ",
    "the compilation operations in a makefile. The program evaluation and review ",
    "technique uses DAGs to model the milestones and activities of large human ",
    "projects, and schedule these projects to use as little total time as possible. ",
    "Combinational logic blocks in electronic circuit design, and the operations ",
    "in dataflow programming languages, involve acyclic networks of processing elements.",
    "DAGs can also represent collections of events and their influence on each other, ",
    "either in a probabilistic structure such as a Bayesian network or as a record of",
    "historical data such as family trees or the version histories of distributed ",
    "revision control systems. DAGs can also be used as a compact representation of ",
    "sequence data, such as the directed acyclic word graph representation of a ",
    "collection of strings, or the binar decision diagram representation of sequences ",
    "of binary choices. More abstractly, the reachability relation in a DAG forms a ",
    "partial order, and any finite partial order may be represented by a DAG using reachability.",
    "Important polynomial time computational problems on DAGs include topological sorting ",
    "(finding a topological ordering), construction of the transitive closure and transitive",
    "reduction (the largest and smallest DAGs with the same reachability relation, respectively), ",
    "and the closure problem, in which the goal is to find a minimum-weight subset of vertices with ",
    "no edges connecting them to the rest of the graph. Transforming a directed graph with cycles ",
    "into a DAG by deleting as few vertices or edges as possible (the feedback vertex set and ",
    "feedback edge set problem, respectively) is NP-hard, but any directed graph can be made ",
    "into a DAG (its condensation) by contracting each strongly connected component into a ",
    "single supervertex. The problems of finding shortest paths and longest paths can be ",
    "solved on DAGs in linear time, in contrast to arbitrary graphs for which shortest path ",
    "algorithms are slower and longest path problems are NP-hard.",
    "The corresponding concept for undirected graphs is a forest, an undirected graph without ",
    "cycles. Choosing an orientation for a forest produces a special kind of directed acyclic graph",
    "called a polytree. However there are many other kinds of directed acyclic graph that are not"]
}

pipe_name = 'orit'
api_server = '{0}/hkube/api-server/api/v1'.format(config.api['base_url'])
pb = PipelineBuilder(pipe_name, api_server_base_url=api_server)
pb.add_node(node_name='green', alg_name='green-alg', input=["@flowInput.tata"])
pb.add_node(node_name='yellow', alg_name='yellow-alg', input=["@green"])
pb.add_node(node_name='black', alg_name='black-alg', input=["@yellow"])
orit_raw = pb.get_raw()
print(orit_raw)

# store pipeline
print('>>>>> STORE ORIT')
pb.store()

# exec stored
print('>>>>> ASYNC EXEC STORED ORIT')
pm = PipelineExecutor(api_server, name=pipe_name, tracker=TrackerType.POLLING)
pm.exec_async()

# delete stored
# print('>>>>> DELETE STORED ORIT')
# pb.delete()

# # exec raw
# print('>>>>> EXEC RAW MOSHE')
# pm1 = PipelineExecutor(api_server, raw=pb.get_raw())
# pm1.exec(input={ "tata": {}})

# print('MORE EXEC...')
# pm.exec(timeout_sec=15)
