import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, LLM

load_dotenv()

# استخدام LLM الخاص بـ CrewAI مباشرة (يدعم Groq)
qto_llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    temperature=0
)

qto_agent = Agent(
    role="Quantity Takeoff Specialist",
    goal="Extract accurate quantities from construction text descriptions",
    backstory="""You are an expert quantity surveyor with 20 years of
    experience in construction. You meticulously extract volumes, areas,
    and counts from project descriptions. You always output structured JSON.""",
    llm=qto_llm,
    verbose=True
)

qto_task = Task(
    description="""
    Extract all construction work items from the following description:
    
    "Living room renovation: Laminate flooring 25 m2, 
    Wall painting 60 m2, Ceiling plasterboard 25 m2, 
    3 electrical outlets"
    
    For each item, extract:
    - item_name (in English)
    - quantity (number)
    - unit (m2, m, count, etc.)
    
    Output ONLY a valid JSON array. No explanations, no markdown.
    """,
    expected_output="A JSON array with fields: item_name, quantity, unit",
    agent=qto_agent
)

qto_crew = Crew(
    agents=[qto_agent],
    tasks=[qto_task],
    verbose=True
)

result = qto_crew.kickoff()
print("\n" + "="*50)
print("النتيجة النهائية:")
print("="*50)
print(result)