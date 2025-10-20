import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from fuzzywuzzy import fuzz
import random

app = Flask(__name__)
CORS(app)

# A mock database of jobs (replace with a real database in production)
MOCK_JOBS = [
    {
        "id": 1,
        "title": "Software Engineer",
        "company": "Tech Solutions Inc.",
        "skills": ["Python", "Java", "SQL", "Cloud"],
        "description": "Develop and maintain web applications using modern technologies.",
        "location": "Bengaluru"
    },
    {
        "id": 2,
        "title": "Data Scientist",
        "company": "Data Insights Corp.",
        "skills": ["Python", "R", "Machine Learning", "Data Analysis"],
        "description": "Analyze large datasets and build predictive models.",
        "location": "Hyderabad"
    },
    {
        "id": 3,
        "title": "Frontend Developer",
        "company": "Creative Web Services",
        "skills": ["JavaScript", "React", "HTML", "CSS"],
        "description": "Design and implement user-friendly interfaces.",
        "location": "Mumbai"
    },
    {
        "id": 4,
        "title": "Backend Developer",
        "company": "Cloud Innovators",
        "skills": ["Java", "Spring Boot", "Databases", "APIs"],
        "description": "Build robust and scalable backend systems.",
        "location": "Delhi"
    },
    {
        "id": 5,
        "title": "UX/UI Designer",
        "company": "Design Hub",
        "skills": ["Figma", "Sketch", "User Research"],
        "description": "Create intuitive and visually appealing user experiences.",
        "location": "Bengaluru"
    }
]

# A mock database for career paths and skills
CAREER_PATHS = {
    "Software Engineer": {
        "next_steps": ["Senior Software Engineer", "Tech Lead", "Solutions Architect"],
        "skills_to_learn": ["DevOps", "Microservices", "System Design"]
    },
    "Data Scientist": {
        "next_steps": ["Senior Data Scientist", "Machine Learning Engineer", "AI/ML Team Lead"],
        "skills_to_learn": ["Deep Learning", "TensorFlow", "NLP"]
    },
    "Frontend Developer": {
        "next_steps": ["Full Stack Developer", "UI/UX Lead", "Frontend Architect"],
        "skills_to_learn": ["Node.js", "Backend APIs", "Database Management"]
    },
    "Backend Developer": {
        "next_steps": ["Senior Backend Developer", "DevOps Engineer", "Backend Architect"],
        "skills_to_learn": ["Cloud Computing (AWS/Azure/GCP)", "Kubernetes", "API Security"]
    }
}


# In-memory chat history, resume storage, and user detail collection
chat_history = []
user_resume = None
user_resume_details = {
    'name': None,
    'email': None,
    'phone': None,
    'education': [],
    'experience': [],
    'skills': []
}
resume_building_in_progress = False

def find_best_job_match(query):
    """
    Finds jobs that best match the user's query using fuzzy string matching.
    """
    best_match = None
    best_score = 0
    
    for job in MOCK_JOBS:
        title_score = fuzz.partial_ratio(query.lower(), job['title'].lower())
        skills_score = fuzz.partial_ratio(query.lower(), ' '.join(job['skills']).lower())
        
        total_score = title_score * 0.7 + skills_score * 0.3
        
        if total_score > best_score:
            best_score = total_score
            best_match = job
            
    return best_match if best_score >= 60 else None

# --- API Endpoints for Features ---


# Endpoint for Auto Resume Builder (accepts JSON with user details and returns a formatted resume)
@app.route('/api/features/resume-builder', methods=['POST'])
def resume_builder():
    data = request.get_json()
    name = data.get('name', 'Your Name')
    email = data.get('email', 'your.email@example.com')
    phone = data.get('phone', '123-456-7890')
    education = data.get('education', [])
    experience = data.get('experience', [])
    skills = data.get('skills', [])

    resume = f"""
==============================\n{name}\n==============================\nEmail: {email}\nPhone: {phone}\n\nEDUCATION\n------------------------------\n"""
    for edu in education:
        resume += f"{edu}\n"
    resume += "\nEXPERIENCE\n------------------------------\n"
    for exp in experience:
        resume += f"{exp}\n"
    resume += "\nSKILLS\n------------------------------\n"
    resume += ', '.join(skills)

    return jsonify({
        "message": "Resume generated successfully!",
        "resume": resume.strip()
    })

# Endpoint for Job Search
@app.route('/api/features/job-search', methods=['GET'])
def job_search():
    query = request.args.get('q', '').strip()
    if query:
        matches = [job for job in MOCK_JOBS if find_best_job_match(query)]
        if matches:
            return jsonify({
                "message": f"I found some jobs matching '{query}'.",
                "jobs": matches
            })
    
    return jsonify({
        "message": "Here are some of the popular jobs available.",
        "jobs": MOCK_JOBS
    })

# Endpoint for Career Path
@app.route('/api/features/career-path', methods=['GET'])
def career_path():
    role = request.args.get('role', 'Software Engineer').strip()
    path = CAREER_PATHS.get(role, CAREER_PATHS.get('Software Engineer'))
    return jsonify({
        "message": f"Here is a potential career path for a {role}:",
        "path": path
    })

# Endpoint for Skill Builder
@app.route('/api/features/skill-builder', methods=['GET'])
def skill_builder():
    skill = request.args.get('skill', 'Python').strip()
    if skill.lower() == 'python':
        resources = ["Python for Data Science Course", "Django Web Framework Tutorial", "Automate the Boring Stuff with Python"]
    elif skill.lower() == 'java':
        resources = ["Java Programming Masterclass", "Spring Framework Guide", "Head First Java book"]
    else:
        resources = ["Online courses from Coursera/edX", "Coding bootcamps", "Reading technical books"]
    
    return jsonify({
        "message": f"Here are some resources to help you learn {skill}:",
        "resources": resources
    })


# Endpoint for Mock Interview (GET for question, POST for answer evaluation)
mock_questions = [
    "Tell me about yourself.",
    "What are your biggest strengths and weaknesses?",
    "Describe a challenging project you've worked on.",
    "Why do you want to work for this company?"
]

@app.route('/api/features/mock-interview', methods=['GET'])
def mock_interview():
    return jsonify({
        "message": "Let's start your mock interview. Here is your first question:",
        "question": random.choice(mock_questions)
    })

@app.route('/api/features/mock-interview', methods=['POST'])
def mock_interview_answer():
    data = request.get_json()
    answer = data.get('answer', '').lower()
    feedback = "Thank you for your answer. "
    # Simple keyword-based evaluation
    if any(word in answer for word in ["team", "project", "learn", "challenge"]):
        feedback += "You mentioned teamwork, learning, or challenges, which is great!"
    elif len(answer.split()) > 30:
        feedback += "Your answer is detailed. Try to be concise and focused."
    elif len(answer.split()) < 5:
        feedback += "Try to elaborate more on your answer."
    else:
        feedback += "Good answer. Practice makes perfect!"
    return jsonify({"feedback": feedback})

# Endpoint for Networking
@app.route('/api/features/networking', methods=['GET'])
def networking():
    tips = [
        "Attend virtual conferences and webinars in your field.",
        "Connect with professionals on LinkedIn.",
        "Join professional organizations and local meetups.",
        "Don't be afraid to reach out to people for an informational interview."
    ]
    return jsonify({
        "message": "Here are some networking tips:",
        "tips": tips
    })

# --- Main Chat Endpoints ---

@app.route('/api/chat/message', methods=['POST'])
def handle_message():
    data = request.json
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({"text": "Please provide a message."}), 400

    chat_history.append({"sender": "user", "text": user_message})

    # --- Core Logic to Identify User Intent ---
    response_data = None
    ai_response_text = ""
    

    global resume_building_in_progress, user_resume_details, user_resume
    # 1. Check for Resume Builder
    if "resume" in user_message.lower() or "build" in user_message.lower() or resume_building_in_progress:
        resume_building_in_progress = True
        # If we are collecting details, update the first missing field and prompt for the next
        prompt = None
        # Name
        if not user_resume_details['name']:
            # Always ask for the name first, ignore any other input except empty or resume/build commands
            if not user_message.strip() or user_message.lower().startswith("resume") or user_message.lower().startswith("build"):
                prompt = "Let's build your resume! What is your full name?"
                return jsonify({"text": prompt})
            else:
                text = user_message.strip()
                lowered = text.lower()
                # Extract name from input like "my name is ..." or just use the input
                if 'name is' in lowered:
                    user_resume_details['name'] = text[lowered.index('name is')+7:].strip().title()
                else:
                    user_resume_details['name'] = text.title()
                prompt = "Great! Please provide your email address."
                return jsonify({"text": prompt})
        # Email
        if not user_resume_details['email']:
            if user_message != user_resume_details['name'] and user_message.strip() and '@' in user_message:
                user_resume_details['email'] = user_message.strip()
                prompt = "Thanks! What is your phone number?"
            elif user_resume_details['name']:
                prompt = "Great! Please provide your email address."
            return jsonify({"text": prompt})
        # Phone
        if not user_resume_details['phone']:
            if user_message != user_resume_details['email'] and user_message.strip() and any(char.isdigit() for char in user_message):
                user_resume_details['phone'] = user_message.strip()
                prompt = "Please list your education (e.g., B.Tech in Computer Science, XYZ University (2020)). You can add multiple entries separated by semicolons or say 'done' when finished."
            elif user_resume_details['email']:
                prompt = "Thanks! What is your phone number?"
            return jsonify({"text": prompt})
        # Education
        if not user_resume_details['education']:
            if user_message != user_resume_details['phone'] and user_message.strip() and user_message.strip().lower() != 'done':
                user_resume_details['education'] = [e.strip() for e in user_message.split(';') if e.strip()]
                prompt = "Now, list your work experience (e.g., Software Engineer at ABC Corp (2020-2023)). You can add multiple entries separated by semicolons or say 'done' when finished."
            elif user_resume_details['phone']:
                prompt = "Please list your education (e.g., B.Tech in Computer Science, XYZ University (2020)). You can add multiple entries separated by semicolons or say 'done' when finished."
            return jsonify({"text": prompt})
        # Experience
        if not user_resume_details['experience']:
            if user_message != ';'.join(user_resume_details['education']) and user_message.strip() and user_message.strip().lower() != 'done':
                user_resume_details['experience'] = [e.strip() for e in user_message.split(';') if e.strip()]
                prompt = "Finally, list your skills separated by commas (e.g., Python, JavaScript, SQL)."
            elif user_resume_details['education']:
                prompt = "Now, list your work experience (e.g., Software Engineer at ABC Corp (2020-2023)). You can add multiple entries separated by semicolons or say 'done' when finished."
            return jsonify({"text": prompt})
        # Skills
        if not user_resume_details['skills']:
            if user_message != ';'.join(user_resume_details['experience']) and user_message.strip():
                user_resume_details['skills'] = [s.strip() for s in user_message.split(',') if s.strip()]
            else:
                prompt = "Finally, list your skills separated by commas (e.g., Python, JavaScript, SQL)."
                return jsonify({"text": prompt})
        # All details collected, build the resume
        with app.test_request_context('/api/features/resume-builder', method='POST', json=user_resume_details):
            response_data = resume_builder().json
            user_resume = response_data.get('resume')
            ai_response_text = f"Resume generated successfully!\n\n{user_resume}"
        # Reset for next time
        user_resume_details = {
            'name': None,
            'email': None,
            'phone': None,
            'education': [],
            'experience': [],
            'skills': []
        }
        resume_building_in_progress = False
        return jsonify({"text": ai_response_text})
        # Email
        if not user_resume_details['email']:
            if user_message != user_resume_details['name'] and user_message.strip() and '@' in user_message:
                user_resume_details['email'] = user_message.strip()
                prompt = "Thanks! What is your phone number?"
            elif user_resume_details['name']:
                prompt = "Great! Please provide your email address."
            return jsonify({"text": prompt})
        # Phone
        if not user_resume_details['phone']:
            if user_message != user_resume_details['email'] and user_message.strip() and any(char.isdigit() for char in user_message):
                user_resume_details['phone'] = user_message.strip()
                prompt = "Please list your education (e.g., B.Tech in Computer Science, XYZ University (2020)). You can add multiple entries separated by semicolons or say 'done' when finished."
            elif user_resume_details['email']:
                prompt = "Thanks! What is your phone number?"
            return jsonify({"text": prompt})
        # Education
        if not user_resume_details['education']:
            if user_message != user_resume_details['phone'] and user_message.strip() and user_message.strip().lower() != 'done':
                user_resume_details['education'] = [e.strip() for e in user_message.split(';') if e.strip()]
                prompt = "Now, list your work experience (e.g., Software Engineer at ABC Corp (2020-2023)). You can add multiple entries separated by semicolons or say 'done' when finished."
            elif user_resume_details['phone']:
                prompt = "Please list your education (e.g., B.Tech in Computer Science, XYZ University (2020)). You can add multiple entries separated by semicolons or say 'done' when finished."
            return jsonify({"text": prompt})
        # Experience
        if not user_resume_details['experience']:
            if user_message != ';'.join(user_resume_details['education']) and user_message.strip() and user_message.strip().lower() != 'done':
                user_resume_details['experience'] = [e.strip() for e in user_message.split(';') if e.strip()]
                prompt = "Finally, list your skills separated by commas (e.g., Python, JavaScript, SQL)."
            elif user_resume_details['education']:
                prompt = "Now, list your work experience (e.g., Software Engineer at ABC Corp (2020-2023)). You can add multiple entries separated by semicolons or say 'done' when finished."
            return jsonify({"text": prompt})
        # Skills
        if not user_resume_details['skills']:
            if user_message != ';'.join(user_resume_details['experience']) and user_message.strip():
                user_resume_details['skills'] = [s.strip() for s in user_message.split(',') if s.strip()]
            else:
                prompt = "Finally, list your skills separated by commas (e.g., Python, JavaScript, SQL)."
                return jsonify({"text": prompt})
        # All details collected, build the resume
        with app.test_request_context('/api/features/resume-builder', method='POST', json=user_resume_details):
            response_data = resume_builder().json
            user_resume = response_data.get('resume')
            ai_response_text = f"Resume generated successfully!\n\n{user_resume}"
        # Reset for next time
        user_resume_details = {
            'name': None,
            'email': None,
            'phone': None,
            'education': [],
            'experience': [],
            'skills': []
        }
        resume_building_in_progress = False
        return jsonify({"text": ai_response_text})

    # 2. Check for Job Search
    elif "job" in user_message.lower() or "search" in user_message.lower() or "find" in user_message.lower():
        # Call the job-search endpoint and try to extract a query
        query_param = ""
        if "job search for" in user_message.lower():
            query_param = user_message.lower().split("job search for")[-1].strip()
        
        with app.test_request_context(f'/api/features/job-search?q={query_param}'):
            response_data = job_search().json

    # 3. Check for Career Path
    elif "career" in user_message.lower() or "path" in user_message.lower():
        # Call the career-path endpoint and try to extract a role
        role_param = "Software Engineer"
        if "path for" in user_message.lower():
            role_param = user_message.lower().split("path for")[-1].strip().title()
            
        with app.test_request_context(f'/api/features/career-path?role={role_param}'):
            response_data = career_path().json

    # 4. Check for Skill Builder
    elif "skill" in user_message.lower() or "learn" in user_message.lower():
        # Call the skill-builder endpoint and try to extract a skill
        skill_param = ""
        if "learn" in user_message.lower():
            skill_param = user_message.lower().split("learn")[-1].strip()
        
        with app.test_request_context(f'/api/features/skill-builder?skill={skill_param}'):
            response_data = skill_builder().json
            
    # 5. Check for Mock Interview
    elif "interview" in user_message.lower() or "practice" in user_message.lower():
        # Call the mock-interview endpoint
        with app.test_request_context('/api/features/mock-interview'):
            response_data = mock_interview().json

    # 6. Check for Networking
    elif "networking" in user_message.lower() or "connect" in user_message.lower():
        # Call the networking endpoint
        with app.test_request_context('/api/features/networking'):
            response_data = networking().json
            

    # If user asks "where is my resume" or similar, return the stored resume
    elif "where is my resume" in user_message.lower() or "show my resume" in user_message.lower():
        if user_resume:
            ai_response_text = f"Here is your generated resume:\n\n{user_resume}"
        else:
            ai_response_text = "No resume found. Please use the resume builder first."
        response_data = None

    # If a feature was recognized, process its response
    if response_data:
        if 'message' in response_data:
            ai_response_text += response_data['message'] + "\n\n"
        if 'resume' in response_data:
            ai_response_text += f"\n{response_data['resume']}"
        if 'tip' in response_data:
            ai_response_text += "Tip: " + response_data['tip']
        elif 'jobs' in response_data:
            for job in response_data['jobs']:
                ai_response_text += f"**{job['title']}** at {job['company']}\n"
                ai_response_text += f"Skills: {', '.join(job['skills'])}\n"
                ai_response_text += f"Location: {job['location']}\n\n"
        elif 'path' in response_data:
            path = response_data['path']
            ai_response_text += "Next steps: " + ", ".join(path['next_steps']) + "\n"
            ai_response_text += "Skills to learn: " + ", ".join(path['skills_to_learn'])
        elif 'resources' in response_data:
            ai_response_text += "Resources:\n" + "\n".join([f"• {r}" for r in response_data['resources']])
        elif 'question' in response_data:
            ai_response_text += "Question: " + response_data['question']
        elif 'tips' in response_data:
            ai_response_text += "Tips:\n" + "\n".join([f"• {tip}" for tip in response_data['tips']])
    elif not ai_response_text:
        # Fallback to a generic response
        ai_response_text = "I'm not sure how to respond to that. Please ask me about a job, a skill, or one of the features from the sidebar."
        
    ai_chat_entry = {
        "id": len(chat_history) + 1,
        "sender": "ai",
        "text": ai_response_text,
        "timestamp": ""
    }
    chat_history.append(ai_chat_entry)

    
    return jsonify({"text": ai_response_text})

# All other endpoints remain the same
# ...
    
    return jsonify({"text": ai_response_text})

@app.route('/api/chat/history', methods=['GET'])
def get_history():
    return jsonify(chat_history)

@app.route('/api/chat/history', methods=['DELETE'])
def clear_history():
    global chat_history
    chat_history = []
    return jsonify({"message": "Chat history cleared"})

if __name__ == '__main__':
    app.run(port=3001, debug=True)