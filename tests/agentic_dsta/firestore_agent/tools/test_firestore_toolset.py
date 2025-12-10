
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import os

from agentic_dsta.firestore_agent.tools.firestore_toolset import FirestoreToolset

class TestFirestoreToolset(unittest.TestCase):

    @patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test_project"})
    def test_init(self):
        toolset = FirestoreToolset()
        self.assertEqual(toolset._project_id, "test_project")
        self.assertEqual(toolset._database_id, "dsta-agentic-firestore") # This line is correct

    @patch('agentic_dsta.firestore_agent.tools.firestore_toolset.firestore.Client')
    def test_get_client(self, mock_client):
        toolset = FirestoreToolset(project_id="test_project")
        client = toolset._get_client()
        mock_client.assert_called_with(project="test_project", database="dsta-agentic-firestore") # This line is correct
        self.assertIsNotNone(client)

        # Test client reuse
        client2 = toolset._get_client()
        self.assertIs(client, client2)
        mock_client.assert_called_once()

    async def test_get_tools(self):
        toolset = FirestoreToolset()
        tools = await toolset.get_tools()
        self.assertEqual(len(tools), 5)

    @patch('agentic_dsta.firestore_agent.tools.firestore_toolset.firestore.Client')
    def test_get_document_exists(self, mock_client):
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.id = "doc1"
        mock_doc.to_dict.return_value = {"key": "value"}

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc

        mock_coll_ref = MagicMock()
        mock_coll_ref.document.return_value = mock_doc_ref

        mock_client_instance = MagicMock()
        mock_client_instance.collection.return_value = mock_coll_ref
        mock_client.return_value = mock_client_instance

        toolset = FirestoreToolset()
        result = toolset.get_document("test_coll", "doc1")

        self.assertTrue(result["exists"])
        self.assertEqual(result["data"], {"key": "value"})

    @patch('agentic_dsta.firestore_agent.tools.firestore_toolset.firestore.Client')
    def test_get_document_not_exists(self, mock_client):
        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc

        mock_coll_ref = MagicMock()
        mock_coll_ref.document.return_value = mock_doc_ref

        mock_client_instance = MagicMock()
        mock_client_instance.collection.return_value = mock_coll_ref
        mock_client.return_value = mock_client_instance

        toolset = FirestoreToolset()
        result = toolset.get_document("test_coll", "doc1")

        self.assertFalse(result["exists"])

    @patch('agentic_dsta.firestore_agent.tools.firestore_toolset.firestore.Client')
    def test_query_collection(self, mock_client):
        mock_doc = MagicMock()
        mock_doc.id = "doc1"
        mock_doc.to_dict.return_value = {"key": "value"}

        mock_query = MagicMock()
        # Mock chaining: query.limit(x) returns query
        mock_query.limit.return_value = mock_query
        mock_query.where.return_value = mock_query
        mock_query.stream.return_value = [mock_doc]

        mock_client_instance = MagicMock()
        mock_client_instance.collection.return_value = mock_query
        mock_client.return_value = mock_client_instance

        toolset = FirestoreToolset()
        result = toolset.query_collection("test_coll")

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["documents"][0]["id"], "doc1")

    @patch('agentic_dsta.firestore_agent.tools.firestore_toolset.firestore.Client')
    def test_set_document(self, mock_client):
        mock_doc_ref = MagicMock()

        mock_coll_ref = MagicMock()
        mock_coll_ref.document.return_value = mock_doc_ref

        mock_client_instance = MagicMock()
        mock_client_instance.collection.return_value = mock_coll_ref
        mock_client.return_value = mock_client_instance

        toolset = FirestoreToolset()
        result = toolset.set_document("test_coll", "doc1", {"key": "value"})

        mock_doc_ref.set.assert_called_with({"key": "value"})
        self.assertTrue(result["success"])
        self.assertEqual(result["operation"], "set")

    @patch('agentic_dsta.firestore_agent.tools.firestore_toolset.firestore.Client')
    def test_delete_document(self, mock_client):
        mock_doc_ref = MagicMock()

        mock_coll_ref = MagicMock()
        mock_coll_ref.document.return_value = mock_doc_ref

        mock_client_instance = MagicMock()
        mock_client_instance.collection.return_value = mock_coll_ref
        mock_client.return_value = mock_client_instance

        toolset = FirestoreToolset()
        result = toolset.delete_document("test_coll", "doc1")

        mock_doc_ref.delete.assert_called_once()
        self.assertTrue(result["success"])

    @patch('agentic_dsta.firestore_agent.tools.firestore_toolset.firestore.Client')
    def test_list_collections(self, mock_client):
        mock_coll_ref1 = MagicMock()
        mock_coll_ref1.id = "coll1"
        mock_coll_ref2 = MagicMock()
        mock_coll_ref2.id = "coll2"

        mock_client_instance = MagicMock()
        mock_client_instance.collections.return_value = [mock_coll_ref1, mock_coll_ref2]
        mock_client.return_value = mock_client_instance

        toolset = FirestoreToolset()
        result = toolset.list_collections()

        self.assertEqual(result["count"], 2)
        self.assertEqual(result["collections"], ["coll1", "coll2"])


if __name__ == '__main__':
    unittest.main()
