from utils import main, graduate_student_into_agent
if __name__ == '__main__':
    main()  # blocking


import student_agents

Agent = graduate_student_into_agent(student_agents.CompositeStudent)
