import { NextResponse } from 'next/server';

export async function GET(request, { params }) {
  const { id } = params;

  try {
    // In a real app, you would fetch the analysis from your database
    // This is a mock response - replace with actual data fetching
    const mockAnalysis = {
      id,
      fileName: 'My_Resume.pdf',
      score: 85,
      skills: ['JavaScript', 'React', 'Node.js', 'Python', 'AWS'],
      experience: '5+ years',
      education: 'BSc in Computer Science',
      strengths: ['Problem Solving', 'Team Leadership', 'Project Management'],
      areasForImprovement: ['Cloud Architecture', 'Machine Learning'],
      recommendations: [
        'Consider obtaining AWS Certification',
        'Learn more about containerization with Docker',
        'Improve your machine learning skills',
        'Add more quantifiable achievements to your resume'
      ],
      // Add more fields as needed
    };

    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 500));

    return NextResponse.json(mockAnalysis);
  } catch (error) {
    console.error('Error fetching analysis:', error);
    return NextResponse.json(
      { error: 'Failed to fetch analysis' },
      { status: 500 }
    );
  }
}
