import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

class GraphManager:
    def __init__(self):
        if not NEO4J_PASSWORD:
            raise ValueError("NEO4J_PASSWORD not found in environment variables.")
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self):
        self.driver.close()

    def initialize_schema(self):
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (i:Investor) REQUIRE i.name IS UNIQUE")

    def load_dual_fetch(self, data_path="../data/sample.json"):
        # Adjust path dynamically relative to the backend directory
        target_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample.json")
        with open(target_path, 'r') as f:
            data = json.load(f)

        target = data.get("target")
        rival = data.get("rival")

        with self.driver.session() as session:
            if target and target.get("company"):
                self._ingest_entity(session, target["company"], target.get("employees", []), "TARGET")
            if rival and rival.get("company"):
                self._ingest_entity(session, rival["company"], rival.get("employees", []), "RIVAL")

    def _ingest_entity(self, session, company, employees, role_label):
        # Create Company Node
        session.execute_write(self._create_company, company, role_label)
        
        # Create Investors
        investors = company.get("backing", {}).get("investor_list", [])
        for inv in investors:
            session.execute_write(self._create_investor_link, company['id'], inv)

        # Create Persons
        for emp in employees:
            session.execute_write(self._create_person, emp, company['id'])

    @staticmethod
    def _create_company(tx, company, role_label):
        query = f"""
        MERGE (c:Company {{id: $id}})
        SET c.name = $name, c.role = $role_label, 
            c.headcount = $headcount, c.funding = $funding
        """
        tx.run(query, 
               id=company.get('id'), 
               name=company.get('name'), 
               role_label=role_label,
               headcount=company.get('muscle', {}).get('headcount', 0),
               funding=company.get('capital', {}).get('funding_total', "$0"))

    @staticmethod
    def _create_investor_link(tx, company_id, investor_name):
        query = """
        MERGE (i:Investor {name: $inv_name})
        WITH i
        MATCH (c:Company {id: $company_id})
        MERGE (i)-[:INVESTS_IN]->(c)
        """
        tx.run(query, inv_name=investor_name, company_id=company_id)

    @staticmethod
    def _create_person(tx, person, company_id):
        ident = person.get("professional_identity", {})
        query = """
        MERGE (p:Person {name: $name}) // using name as id for mock
        SET p.title = $title, p.seniority = $seniority, p.department = $department
        WITH p
        MATCH (c:Company {id: $company_id})
        MERGE (p)-[:WORKS_AT]->(c)
        """
        tx.run(query, 
               name=ident.get("full_name"),
               title=ident.get("current_title"),
               seniority=ident.get("seniority_level"),
               department=ident.get("department"),
               company_id=company_id)

    def detect_boardroom_traitors(self):
        """
        Identifies investors who are backing both the TARGET and the RIVAL company.
        """
        query = """
        MATCH (t:Company {role: 'TARGET'})<-[:INVESTS_IN]-(i:Investor)-[:INVESTS_IN]->(r:Company {role: 'RIVAL'})
        RETURN i.name AS traitor_investor, t.name AS target, r.name AS rival
        """
        traitors = []
        with self.driver.session() as session:
            result = session.run(query)
            for record in result:
                traitors.append({
                    "investor": record["traitor_investor"],
                    "target": record["target"],
                    "rival": record["rival"]
                })
        return traitors

if __name__ == "__main__":
    manager = GraphManager()
    try:
        manager.initialize_schema()
        manager.load_dual_fetch()
        traitors = manager.detect_boardroom_traitors()
        print(f"Knowledge Graph updated. Found {len(traitors)} Boardroom Traitors.")
        if traitors:
            print("Leaks:", traitors)
    finally:
        manager.close()
