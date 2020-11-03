"""Implement the scientific extension.

DOI Handbook: https://doi.org/10.1000/182

https://github.com/radiantearth/stac-spec/tree/dev/extensions/scientific
"""

import copy
import re
from typing import Dict, List, Optional, TypeVar
from urllib import parse

import pystac
from pystac import collection
from pystac import Extensions
from pystac import item
from pystac import link
from pystac.extensions import base

PREFIX: str = 'sci:'
DOI: str = PREFIX + 'doi'
CITATION: str = PREFIX + 'citation'
PUBLICATIONS: str = PREFIX + 'publications'

# Link type.
CITE_AS: str = 'cite-as'

# TODO(schwehr): What is the correct regex for doi?
# https://github.com/radiantearth/stac-spec/issues/910
DOI_REGEX = r'10[.][0-9]{4}([.][0-9]+)*/.+'
DOI_URL_BASE = 'https://doi.org/'

_PublicationType = TypeVar('Publication')
_ScientificItemExtType = TypeVar('ScientificItemExt')
_ScientificCollectionExtType = TypeVar('ScientificCollectionExtType')


def is_doi_valid(doi: str) -> bool:
    return bool(re.match(DOI_REGEX, doi))


def doi_to_url(doi: str) -> str:
    return DOI_URL_BASE + parse.quote(doi)


class Publication:
    """Helper for Publication entries."""
    def __init__(self, doi: str, citation: str) -> None:
        self.doi = doi
        self.citation = citation

    def __eq__(self, other: _PublicationType) -> bool:
        if not isinstance(other, Publication):
            return NotImplemented

        return self.doi == other.doi and self.citation == other.citation

    def __repr__(self) -> str:
        return f'<Publication doi={self.doi} target={self.citation}>'

    def to_dict(self) -> Dict[str, str]:
        return copy.deepcopy({'doi': self.doi, 'citation': self.citation})

    @staticmethod
    def from_dict(d: Dict[str, str]) -> _PublicationType:
        return Publication(d['doi'], d['citation'])

    def get_link(self) -> link.Link:
        return link.Link(CITE_AS, doi_to_url(self.doi))


def remove_link(links: List[link.Link], pub: Publication):
    url = doi_to_url(pub.doi)
    for i, a_link in enumerate(links):
        if a_link.rel != CITE_AS:
            continue
        if a_link.target == url:
            del links[i]
            break


class ScientificItemExt(base.ItemExtension):
    """Add an citation and dois to a STAC Item."""
    def __init__(self, an_item: item.Item) -> None:
        self.item = an_item

    def apply(self,
              doi: Optional[str] = None,
              citation: Optional[str] = None,
              publications: Optional[List[Publication]] = None) -> None:
        if doi:
            self.doi = doi
        if citation:
            self.citation = citation
        if publications:
            self.publications = publications

    @classmethod
    def from_item(cls: _ScientificItemExtType, an_item: item.Item) -> _ScientificItemExtType:
        return cls(an_item)

    @classmethod
    def _object_links(cls: _ScientificItemExtType) -> List:
        return []

    @property
    def doi(self) -> str:
        return self.item.properties.get(DOI)

    @doi.setter
    def doi(self, v: str) -> None:
        self.item.properties[DOI] = v
        url = doi_to_url(self.doi)  # TODO(schwehr): Remove links for doi
        self.item.add_link(pystac.link.Link(CITE_AS, url))

    @property
    def citation(self) -> str:
        return self.item.properties.get(CITATION)

    @citation.setter
    def citation(self, v: str) -> None:
        self.item.properties[CITATION] = v

    @property
    def publications(self) -> List[Publication]:
        return [Publication.from_dict(pub) for pub in self.item.properties.get(PUBLICATIONS, [])]

    @publications.setter
    def publications(self, v: List[Publication]) -> None:
        self.item.properties[PUBLICATIONS] = [pub.to_dict() for pub in v]
        for pub in v:
            self.item.add_link(pub.get_link())

    # None for publication will clear all.
    def remove_publication(self, publication: Optional[Publication] = None) -> None:
        if PUBLICATIONS not in self.item.properties:
            return

        if not publication:
            for one_pub in self.item.ext.scientific.publications:
                remove_link(self.item.links, one_pub)

            del self.item.properties[PUBLICATIONS]
            return

        # One publication and link to remove
        remove_link(self.item.links, publication)
        to_remove = publication.to_dict()
        self.item.properties[PUBLICATIONS].remove(to_remove)

        if not self.item.properties[PUBLICATIONS]:
            del self.item.properties[PUBLICATIONS]


class ScientificCollectionExt(base.CollectionExtension):
    """Add an citation and dois to a STAC Collection."""
    def __init__(self, a_collection):
        self.collection = a_collection

    def apply(self,
              doi: Optional[str] = None,
              citation: Optional[str] = None,
              publications: Optional[List[Publication]] = None):
        if doi:
            self.doi = doi
        if citation:
            self.citation = citation
        if publications:
            self.publications = publications

    @classmethod
    def from_collection(cls: _ScientificCollectionExtType,
                        a_collection: collection.Collection) -> _ScientificCollectionExtType:
        return cls(a_collection)

    @classmethod
    def _object_links(cls: _ScientificCollectionExtType) -> List:
        return []

    @property
    def doi(self) -> str:
        return self.collection.extra_fields.get(DOI)

    @doi.setter
    def doi(self, v: str) -> None:
        self.collection.extra_fields[DOI] = v
        url = doi_to_url(self.doi)  # TODO(schwehr) Remove.
        self.collection.add_link(pystac.link.Link(CITE_AS, url))

    @property
    def citation(self) -> str:
        return self.collection.extra_fields.get(CITATION)

    @citation.setter
    def citation(self, v: str) -> None:
        self.collection.extra_fields[CITATION] = v

    @property
    def publications(self) -> List[Publication]:
        return [
            Publication.from_dict(p) for p in self.collection.extra_fields.get(PUBLICATIONS, [])
        ]

    @publications.setter
    def publications(self, v: List[Publication]) -> None:
        self.collection.extra_fields[PUBLICATIONS] = [pub.to_dict() for pub in v]
        for pub in v:
            self.collection.add_link(pub.get_link())

    # None for publication will clear all.
    def remove_publication(self, publication: Optional[Publication] = None) -> None:
        if PUBLICATIONS not in self.collection.extra_fields:
            return

        if not publication:
            for one_pub in self.collection.ext.scientific.publications:
                remove_link(self.collection.links, one_pub)

            del self.collection.extra_fields[PUBLICATIONS]
            return

        # One publication and link to remove
        remove_link(self.collection.links, publication)
        to_remove = publication.to_dict()
        self.collection.extra_fields[PUBLICATIONS].remove(to_remove)

        if not self.collection.extra_fields[PUBLICATIONS]:
            del self.collection.extra_fields[PUBLICATIONS]


SCIENTIFIC_EXTENSION_DEFINITION = base.ExtensionDefinition(Extensions.SCIENTIFIC, [
    base.ExtendedObject(item.Item, ScientificItemExt),
    base.ExtendedObject(collection.Collection, ScientificCollectionExt)
])
