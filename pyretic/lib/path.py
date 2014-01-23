################################################################################
# The Pyretic Project                                                          #
# frenetic-lang.org/pyretic                                                    #
# author: Srinivas Narayana (narayana@cs.princeton.edu)                        #
################################################################################
# Licensed to the Pyretic Project by one or more contributors. See the         #
# NOTICES file distributed with this work for additional information           #
# regarding copyright and ownership. The Pyretic Project licenses this         #
# file to you under the following license.                                     #
#                                                                              #
# Redistribution and use in source and binary forms, with or without           #
# modification, are permitted provided the following conditions are met:       #
# - Redistributions of source code must retain the above copyright             #
#   notice, this list of conditions and the following disclaimer.              #
# - Redistributions in binary form must reproduce the above copyright          #
#   notice, this list of conditions and the following disclaimer in            #
#   the documentation or other materials provided with the distribution.       #
# - The names of the copyright holds and contributors may not be used to       #
#   endorse or promote products derived from this work without specific        #
#   prior written permission.                                                  #
#                                                                              #
# Unless required by applicable law or agreed to in writing, software          #
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT    #
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the     #
# LICENSE file distributed with this work for specific language governing      #
# permissions and limitations under the License.                               #
################################################################################

from pyretic.core.language import identity, egress_network, Filter, drop, match, modify, Query, FwdBucket, CountBucket
from pyretic.lib.query import counts, packets
import subprocess
import pyretic.vendor
import pydot

#############################################################################
### Basic classes for generating path atoms and creating path expressions ###
#############################################################################

TOKEN_START_VALUE = 48 # start with printable ASCII for visual inspection ;)

class CharacterGenerator:
    """ Generate characters to represent equivalence classes of existing match
    predicates. `get_token` returns the same token value as before if a policy
    already seen (and hence recorded in its map) is provided to it.
    """
    token = TOKEN_START_VALUE
    filter_to_token = {}
    token_to_filter = {}
    token_to_tokens = {}

    @classmethod
    def clear(cls):
        cls.token = TOKEN_START_VALUE
        cls.filter_to_token = {}
        cls.token_to_filter = {}
        cls.token_to_tokens = {}

    @classmethod
    def has_nonempty_intersection(cls, p1, p2):
        """Return True if policies p1, p2 have an intesection which is
        drop. Works by generating the classifiers for the intersection of the
        policies, and checking if there are anything other than drop rules.
        """
        def get_classifier(p):
            if p._classifier:
                return p._classifier
            return p.generate_classifier()

        int_class = get_classifier(p1 & p2)
        for rule in int_class.rules:
            if not drop in rule.actions:
                return True
        return False

    @classmethod
    def add_new_filter(cls, new_filter):
        def add_new_token(pol):
            new_token = cls.__new_token__()
            cls.filter_to_token[pol] = new_token
            cls.token_to_filter[new_token] = pol
            return new_token

        # The algorithm below ensures that matches are disjoint before adding
        # them. Basically, each character that is present in the path
        # expressions represents a mutually exclusive packet match.
        diff_list = drop
        new_intersecting_tokens = []
        for existing_filter in cls.token_to_filter.values():
            if cls.has_nonempty_intersection(existing_filter, new_filter):
                tok = cls.filter_to_token[existing_filter]
                if cls.has_nonempty_intersection(existing_filter, ~new_filter):
                    # do actions below only if the existing filter has some
                    # intersection with, but is not completely contained in, the
                    # new filter.
                    del cls.filter_to_token[existing_filter]
                    del cls.token_to_filter[tok]
                    new_tok1 = add_new_token(existing_filter & ~new_filter)
                    new_tok2 = add_new_token(existing_filter & new_filter)
                    cls.token_to_tokens[tok] = [new_tok1, new_tok2]
                    new_intersecting_tokens.append(new_tok2)
                else:
                    # i.e., if existing filter is completely contained in new one.
                    new_intersecting_tokens.append(tok)
                # add existing_filter into list of policies to be subtracted as
                # long as there is some intersection.
                if diff_list == drop:
                    diff_list = existing_filter
                else:
                    diff_list = diff_list | existing_filter
        # add the new_filter itself, differenced by all the intersecting parts.
        if diff_list != drop: # i.e., if there was intersection with existing filters
            new_token = cls.__new_token__()
            new_disjoint_token = []
            if cls.has_nonempty_intersection(new_filter, ~diff_list):
                # i.e., if the intersections didn't completely make up the new filter
                new_disjoint_token.append(add_new_token(new_filter & ~diff_list))
            cls.token_to_tokens[new_token] = new_intersecting_tokens + new_disjoint_token
        else:
            # i.e., if there was no intersection at all with existing filters
            new_token = add_new_token(new_filter)
        return new_token

    @classmethod
    def get_filter_from_token(cls, tok):
        if tok in cls.token_to_filter:
            return cls.token_to_filter[tok]
        elif tok in cls.token_to_tokens:
            toklist = cls.token_to_tokens[tok]
            tok0 = toklist[0]
            output_filter = cls.get_filter_from_token(tok0)
            for new_tok in toklist[1:]:
                output_filter = output_filter | cls.get_filter_from_token(new_tok)
            return output_filter
        else:
            raise TypeError

    @classmethod
    def get_filter_from_edge_label(cls, edge_label):
        """Recursive search in token_to_tokens, or just direct return from
        token_to_filter, for any token.
        """
        tok0 = cls.get_token_from_char(edge_label[0])
        assert tok0 in cls.token_to_filter
        output_filter = cls.token_to_filter[tok0]
        for char in edge_label[1:]:
            tok = cls.get_token_from_char(char)
            assert tok in cls.token_to_filter
            output_filter = output_filter | cls.token_to_filter[tok]
        return output_filter

    @classmethod
    def get_token(cls, pol):
        if pol in cls.filter_to_token:
            return cls.filter_to_token[pol]
        else:
            return cls.add_new_filter(pol)

    @classmethod
    def get_char_from_token(cls, tok):
        try:
            return chr(tok)
        except:
            return unichr(tok)

    @classmethod
    def get_token_from_char(cls, char):
        return ord(char)

    @classmethod
    def char_in_lexer_language(cls, char):
        return char in ['*','+','|','{','}','(',
                       ')','-','^','.','&','?',
                       '"',"'",'%','$',',','/',"\\"]

    @classmethod
    def __new_token__(cls):
        cls.token += 1
        char = cls.get_char_from_token(cls.token)
        if cls.char_in_lexer_language(char):
            return cls.__new_token__()
        return cls.token

    @classmethod
    def get_terminal_expression(cls, expr):
        def get_terminal_expr_for_char(c):
            tok = cls.get_token_from_char(c)
            if not tok in cls.token_to_tokens:
                assert tok in cls.token_to_filter or cls.char_in_lexer_language(c)
                return c
            else:
                terminal_expr = '('
                for tok2 in cls.token_to_tokens[tok]:
                    c2 = cls.get_char_from_token(tok2)
                    terminal_expr += get_terminal_expr_for_char(c2) + '|'
                terminal_expr = terminal_expr[:-1] + ')'
                return terminal_expr

        new_expr = ''
        for c in expr:
            new_expr += get_terminal_expr_for_char(c)
        return new_expr


class path(Query):
    """A way to query packets or traffic volumes satisfying regular expressions
    denoting paths of located packets.

    :param a: path atom used to construct this path element
    :type atom: atom
    """
    def __init__(self, a=None, expr=None):
        if a:
            assert isinstance(a, atom)
            self.atom = a
            self.expr = CharacterGenerator.get_char_from_token(self.atom.token)
        elif expr:
            assert isinstance(expr, str)
            self.expr = expr
        else:
            raise RuntimeError
        super(path, self).__init__()

    def __repr__(self):
        return '[path expr: ' + self.expr + ' id: ' + str(id(self)) + ']'

    def __xor__(self, other):
        """Implementation of the path concatenation operator ('^')"""
        assert isinstance(other, path)
        return path(expr=(self.expr + other.expr))

    def __or__(self, other):
        """Implementation of the path alternation operator ('|')"""
        assert isinstance(other, path)
        return path(expr=('(' + self.expr + ')|(' + other.expr + ')'))

    def __pos__(self):
        """Implementation of the Kleene star operator.

        TODO(ngsrinivas): It just looks wrong to use '+' instead of '*', but
        unfortunately there is no unary (prefix or postfix) '*' operator in
        python.
        """
        return path(expr=('(' + self.expr + ')*'))

    @classmethod
    def clear(cls):
        cls.re_list = []
        cls.paths_list = []
        cls.path_to_bucket = {}

    @classmethod
    def append_re_without_intersection(cls, new_re, p):
        du = dfa_utils
        i = 0
        diff_re_list = []
        length = len(cls.re_list)
        for i in range(0, length):
            existing_re = cls.re_list[i]
            if du.re_equals(existing_re, new_re):
                cls.paths_list[i] += [p]
                return False
            elif du.re_belongs_to(existing_re, new_re):
                cls.paths_list[i] += [p]
                diff_re_list.append(existing_re)
            elif du.re_has_nonempty_intersection(existing_re, new_re):
                # separate out the intersecting and non-intersecting parts
                # non-intersecting part first:
                cls.re_list[i] = '(' + existing_re + ') & ~(' + new_re + ')'
                # create a new expression for the intersecting part:
                intersection_re = '(' + existing_re + ') & (' + new_re + ')'
                cls.re_list.append(intersection_re)
                cls.paths_list.append(cls.paths_list[i] + [p])
                diff_re_list.append(existing_re)
            # Finally, we do nothing if there is no intersection at all.
            i += 1
        # So far we've handled intersecting parts with existing res. Now deal
        # with the intersecting parts of the new re.
        new_nonintersecting_re = new_re
        if diff_re_list:
            all_intersecting_parts = reduce(lambda x,y: x + '|' + y,
                                            diff_re_list)
            if not du.re_belongs_to(new_re, all_intersecting_parts):
                # there's some part of the new expression that's not covered by
                # any of the existing expressions.
                new_nonintersecting_re = ('(' + new_re + ') & ~(' +
                                          all_intersecting_parts + ')')
            else:
                # the new expression was already covered by (parts) of existing
                # expressions, and we've already added path references for those.
                return False
        # add just the non-overlapping parts of the new re to the re_list.
        cls.re_list.append(new_nonintersecting_re)
        cls.paths_list.append([p])
        return True

    @classmethod
    def finalize(cls, p):
        """Add a path into the set of final path queries that will be
        compiled. This is explicitly needed since at the highest level there is
        no AST for the paths.

        :param p: path to be finalized for querying (and hence compilation).
        :type p: path
        """
        def register_callbacks(bucket, callbacks):
            for f in callbacks:
                bucket.register_callback(f)

        # ensure finalization structures exist
        try:
            if cls.re_list and cls.paths_list and cls.path_to_bucket:
                pass
        except:
            cls.re_list = [] # str list
            cls.paths_list = [] # path list list
            cls.path_to_bucket = {} # dict path: bucket

        # modify finalization structures to keep track of newly added expression
        fb = FwdBucket() ### XXX generalize later to other buckets.
        register_callbacks(fb, p.callbacks)
        expr = CharacterGenerator.get_terminal_expression(p.expr)
        cls.append_re_without_intersection(expr, p)
        cls.path_to_bucket[p] = fb

    @classmethod
    def get_policy_fragments(cls):
        """Generates tagging and counting policy fragments to use with the
        returned general network policy.
        """
        du = dfa_utils
        cg = CharacterGenerator
        dfa = du.regexes_to_dfa(cls.re_list, '/tmp/pyretic-regexes.txt')

        def set_tag(val):
            return modify({'vlan_id': int(val), 'vlan_pcp': 0})

        def match_tag(val):
            if int(val) == 0:
                return match({'vlan_id': 0xffff, 'vlan_pcp': 0})
            return match({'vlan_id': int(val), 'vlan_pcp': 0})

        tagging_policy = drop
        untagged_packets = identity
        counting_policy = drop
        edge_list = du.get_edges(dfa)

        for edge in edge_list:
            # generate tagging fragment
            src = du.get_state_id(du.get_edge_src(edge, dfa))
            dst = du.get_state_id(du.get_edge_dst(edge, dfa))
            edge_label = du.get_edge_label(edge)
            if len(edge_label) > 1: # character class
                edge_label = edge_label[1:-1] # strip off '[' and ']'
            transit_match = cg.get_filter_from_edge_label(edge_label)
            tagging_match = match_tag(src) & transit_match
            tagging_policy += (tagging_match >> set_tag(dst))
            untagged_packets = untagged_packets & ~tagging_match

            # generate counting fragment, if accepting state.
            dst_state = du.get_edge_dst(edge, dfa)
            if du.is_accepting(dst_state):
                accepted_token = du.get_accepted_token(dst_state)
                paths = cls.paths_list[accepted_token]
                for p in paths:
                    bucket = cls.path_to_bucket[p]
                    counting_policy += ((match_tag(src) & transit_match) >>
                                        bucket)

        # preserve untagged packets as is for forwarding.
        tagging_policy += untagged_packets

        # remove all tags before passing on to hosts.
        untagging_policy = ((egress_network() >>
                             modify(vlan_id=None,vlan_pcp=None)) +
                            (~egress_network()))
        return [tagging_policy, untagging_policy, counting_policy]

    @classmethod
    def compile(cls, path_pols):
        """Stitch together the "single packet policy" and "path policy" and
        return the globally effective network policy.

        :param path_pols: a list of path queries
        :type path_pols: path list
        :param single_pkt_pol: main forwarding (single pkt) policy set by
        application
        :type single_pkt_pol: Policy
        """
        for p in path_pols:
            cls.finalize(p)
        return cls.get_policy_fragments()

class atom(path, Filter):
    """A single atomic match in a path expression.
    
    :param m: a Filter (or match) object used to initialize the path atom.
    :type match: Filter
    """
    def __init__(self, m):
        assert isinstance(m, Filter)
        self.policy = m
        self.token = CharacterGenerator.get_token(m)
        super(atom, self).__init__(a=self)

    def __and__(self, other):
        assert isinstance(other, atom)
        return atom(self.policy & other.policy)

    def __add__(self, other):
        # This won't actually work because the '+' operation results in an
        # object of type parallel, which is not a Filter.
        assert isinstance(other, atom)
        return atom(self.policy + other.policy)

    def __sub__(self, other):
        assert isinstance(other, atom)
        return atom((~other.policy) & self.policy)

    def __invert__(self):
        return atom(~(self.policy))

#############################################################################
###        Utilities to get data into ml-ulex, and out into DFA           ###
#############################################################################

class dfa_utils:

    @classmethod
    def get_lexer_input(cls, re_list):
        """Return a string formatted such that ml-ulex could take it as input for
        generating a scanner.

        :param re_list: list of regular expressions in ml-ulex format.
        :type re_list: str list
        """
        lex_input = ''
        expr_num = 0
        for r in re_list:
            lex_input += (r + ' => ( T.expr_' + str(expr_num) + ' );')
            lex_input += '\n'
            expr_num += 1
        return lex_input

    @classmethod
    def write_string(cls, string, filename):
        """Write the provided input string into a file.

        :param string: string input to be written into temporary file.
        :type string: str
        :param filename: name of file to be written into
        :type filename: str
        """
        try:
            f = open(filename, 'w')
            f.write(string)
            f.close()
        except:
            print error
            print "There was an error in writing the input to file!"

    @classmethod
    def run_ml_ulex(cls, inp_file):
        try:
            output = subprocess.check_output(["ml-ulex", "--dot", inp_file])
        except subprocess.CalledProcessError:
            print "ERROR: There was an error in running ml-ulex!"
        return output

    @classmethod
    def sort_states(cls, states_list):
        get_index = lambda s: int(s.get_name()[1:])
        cmpfunc = lambda x, y: cmp(get_index(x), get_index(y))
        return sorted(states_list, cmpfunc)

    @classmethod
    def print_dfa(cls, g):
        """Print the extracted DFA from the dot file.

        :param g: graph object extracted from pydot.
        :type g: Graph (pydot class)
        """
        output = "States:\n"
        states_list = [n for n in g.get_node_list() if n.get_name() != 'graph']
        for node in cls.sort_states(states_list):
            output += node.get_name()
            if cls.is_accepting(node):
                output += ': accepting state for expression '
                output += str(cls.get_accepted_token(node))
            output += "\n"
        output += "\nTransitions:"
        for edge in g.get_edge_list():
            src = edge.get_source()
            dst = edge.get_destination()
            label = edge.get_label()
            output += (src + ' --> ' + label + ' --> ' + dst + '\n')
        print output
        return output

    @classmethod
    def get_state_id(cls, s):
        return (s.get_name())[1:]

    @classmethod
    def get_states(cls, g):
        return [n for n in g.get_node_list() if n.get_name() != 'graph']

    @classmethod
    def get_edge_src(cls, e, g):
        """Get the source node object of an edge.

        :param e: edge object
        :type e: Edge
        :param g: graph object
        :type g: Graph
        """
        return g.get_node(e.get_source())[0]

    @classmethod
    def get_edge_dst(cls, e, g):
        return g.get_node(e.get_destination())[0]

    @classmethod
    def get_edge_label(cls, e):

        def get_chars_in_range(low, high):
            chars = ''
            cg = CharacterGenerator
            for t in range(ord(low), ord(high)):
                chars += cg.get_char_from_token(t)
            return chars

        def get_enumerated_labels(label):
            """Get enumerated labels from a character class representation, with
            potential abbreviations of ranges.
            """
            label_sets = label.split('-')
            num_ranges = len(label_sets)
            if num_ranges == 1:
                return label
            else:
                enumerated_label = ''
                num_ranges = len(label_sets)
                for i in range(0, num_ranges):
                    if len(label_sets[i]) == 0:
                        raise RuntimeError # expect valid character classes.
                    enumerated_label += label_sets[i][:-1]
                    if i < (num_ranges-1):
                        enumerated_label += (get_chars_in_range(
                                label_sets[i][-1],
                                label_sets[i+1][0]))
                    else:
                        # last character isn't part of any more ranges.
                        enumerated_label += label_sets[i][-1]
                return enumerated_label

        return get_enumerated_labels(e.get_label()[1:-1])

    @classmethod
    def get_edges(cls, g):
        return g.get_edge_list()

    @classmethod
    def get_num_states(cls, g):
        return len(cls.get_states(g))

    @classmethod
    def get_num_transitions(cls, g):
        return len(g.get_edge_list())

    @classmethod
    def is_accepting(cls, s):
        return s.get_shape() == '"doublecircle"'

    @classmethod
    def get_accepted_token(cls, s):
        assert cls.is_accepting(s)
        return int(s.get_label().split('/')[1].split('"')[0])

    @classmethod
    def get_num_accepting_states(cls, g):
        states_list = cls.get_states(g)
        num = 0
        for node in cls.sort_states(states_list):
            if cls.is_accepting(node):
                num += 1
        return num

    @classmethod
    def regexes_to_dfa(cls, re_list, tmp_ml_ulex_file):
        lexer_str = cls.get_lexer_input(re_list)
        cls.write_string(lexer_str, tmp_ml_ulex_file)
        ml_ulex_out = cls.run_ml_ulex(tmp_ml_ulex_file)
        tmp_dot  = tmp_ml_ulex_file + ".dot"
        return pydot.graph_from_dot_file(tmp_dot)

    @classmethod
    def intersection_is_null(cls, re1, re2, tmp_file='/tmp/pyretic-regexes-int.txt'):
        """Determine if the intersection of two regular expressions is null.

        :param re1, re2: regular expressions in string format
        :type re1, re2: str
        """
        re = ['(' + re1 + ') & (' + re2 + ')']
        dfa = cls.regexes_to_dfa(re, tmp_file)
        return (cls.get_num_accepting_states(dfa) == 0)

    @classmethod
    def re_equals(cls, re1, re2):
        """Determine if two regular expressions are equal."""
        nre1 = '~(' + re1 + ')'
        nre2 = '~(' + re2 + ')'
        return (cls.intersection_is_null(re1, nre2) and
                cls.intersection_is_null(nre1, re2))

    @classmethod
    def re_belongs_to(cls, re1, re2):
        """Return True if re1 is a subset of re2 (including equals), and False
        otherwise.
        """
        nre2 = '~(' + re2 + ')'
        return cls.intersection_is_null(re1, nre2)

    @classmethod
    def re_has_nonempty_intersection(cls, re1, re2):
        return not cls.intersection_is_null(re1, re2)
