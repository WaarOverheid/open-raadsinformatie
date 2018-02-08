import owl
from .namespaces import FOAF, ORG
from owltology.property import Relation


class Agent(owl.Thing):
    has_member = Relation(ORG, 'hasMember')

    class Meta:
        namespace = FOAF


class Group(Agent):
    member = Relation(ORG, 'member')

    class Meta:
        namespace = FOAF
