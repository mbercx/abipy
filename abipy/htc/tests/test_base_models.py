#from pprint import pprint
import mongomock

from typing import List
from pydantic.main import ModelMetaclass
from pymatgen.core.structure import Structure as pmg_Structure
from abipy.core.testing import AbipyTest
from abipy.core.structure import Structure as abi_Structure
from abipy.abio.inputs import AbinitInput
from abipy.htc.base_models import AbipyModel, MongoConnector, QueryResults, MongoModel, mongo_insert_models


class SubModel(AbipyModel):
    abi_structure: abi_Structure


class TopModel(MongoModel):
    pmg_structure: pmg_Structure
    submodel: SubModel
    class_type: ModelMetaclass = SubModel
    items: List[int] = [1, 2, 3]
    abinit_input: AbinitInput


class TestAbipyBaseModels(AbipyTest):

    def test_base_models(self):

        pmg_structure = self.get_structure("Si")  # This is a pymatgen structure.
        abi_structure = abi_Structure.as_structure(self.get_structure("Si"))  # This is an Abipy structure.

        sub_model = SubModel(abi_structure=abi_structure)
        abinit_input = self.get_gsinput_si()
        top_model = TopModel(pmg_structure=pmg_structure, submodel=sub_model, abinit_input=abinit_input)

        # Test pydantic API
        pydantic_json_string = top_model.json()
        assert "TopModel" not in pydantic_json_string

        monty_json_string = top_model.to_json()
        assert "TopModel" in monty_json_string

        monty_dict = top_model.as_dict()
        same_top_model = TopModel.from_dict(monty_dict)

        assert same_top_model.class_type is SubModel

        assert isinstance(pmg_structure, pmg_Structure)
        assert same_top_model.pmg_structure == pmg_structure
        assert isinstance(same_top_model.submodel.abi_structure, abi_Structure)
        assert same_top_model.submodel.abi_structure == pmg_structure
        #assert same_top_model.abinit_input == abinit_input
        #self.assertMSONable(top_model, test_if_subclass=True)
        #assert 0

        collection = mongomock.MongoClient().db.collection
        oid = top_model.mongo_insert(collection)
        assert oid
        same_model = TopModel.from_mongo_oid(oid, collection)
        assert same_model.pmg_structure == pmg_structure
        same_model.mongo_full_update_oid(oid, collection)

        models = [top_model, same_model]
        oids = mongo_insert_models(models, collection)
        assert len(oids) == 2

        query = {}
        qr = TopModel.mongo_find(query, collection)
        assert bool(qr) and len(qr) == 3
        assert len(qr.models) == 3
        assert set(qr.oids) == set(oids + [oid])

    def test_mongo_connector(self):
        connector = MongoConnector(host="example.com", port=27017, collection_name="collection_name")
        assert connector.host == "example.com"
        assert str(connector.port) in connector._repr_markdown_()

        connector = MongoConnector.for_localhost(collection_name="foobar")
        assert "foobar" in connector._repr_markdown_()
        self.assertMSONable(connector, test_if_subclass=True)

        #collection = connector.get_collection()
        #connector.open_mongoflow_gui(**serve_kwargs)

    def test_query_results_api(self):
        query = {"_id": "foo"}
        qr = QueryResults.empty_from_query(query)
        assert qr.query == query
        assert not qr
        assert len(qr) == 0