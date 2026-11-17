"""Create/update the Entra-authenticated Azure AI Search connection and the sop-advisor agent.

Run from the developer machine after `az login`. Needs the Foundry project resource id and the Search resource id
(env FOUNDRY_PROJECT_RESOURCE_ID / SEARCH_RESOURCE_ID or flags). No keys are used: the connection authenticates with
the Foundry project's managed identity.
"""
import argparse
import json
import urllib.request

import _setup  # noqa: F401

from knowledge_enrichment.agents import create_or_update_agent
from knowledge_enrichment.agents.advisor import project_client
from knowledge_enrichment.kb import get_credential
from knowledge_enrichment.settings import get_settings

ARM = "https://management.azure.com"
API = "2025-06-01"


def put_connection(project_resource_id: str, name: str, search_endpoint: str, search_resource_id: str, location: str) -> None:
    token = get_credential().get_token(f"{ARM}/.default").token
    body = {
        "properties": {
            "category": "CognitiveSearch",
            "target": search_endpoint.rstrip("/") + "/",
            "authType": "AAD",
            "isSharedToAll": False,
            "metadata": {"ApiType": "Azure", "ResourceId": search_resource_id, "location": location, "type": "azure_ai_search"},
        }
    }
    req = urllib.request.Request(
        f"{ARM}{project_resource_id}/connections/{name}?api-version={API}",
        data=json.dumps(body).encode(), method="PUT",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        print("Connection upserted:", resp.status)


def main() -> None:
    s = get_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-resource-id", default=s.foundry_project_resource_id)
    parser.add_argument("--search-resource-id", default=s.search_resource_id)
    parser.add_argument("--search-location", default=s.search_location)
    args = parser.parse_args()
    if not args.project_resource_id or not args.search_resource_id:
        parser.error("FOUNDRY_PROJECT_RESOURCE_ID and SEARCH_RESOURCE_ID are required (env, .env or flags)")

    put_connection(args.project_resource_id, s.search_connection_name, s.search_endpoint, args.search_resource_id, args.search_location)

    with project_client(s) as project:
        connection = project.connections.get(s.search_connection_name)
        print("Connection id:", connection.id)
    agent = create_or_update_agent(s, connection.id)
    print(f"Agent '{agent.name}' version {agent.version} created.")


if __name__ == "__main__":
    main()
