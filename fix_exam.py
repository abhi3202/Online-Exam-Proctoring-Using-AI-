# Fix exam.html to show proctoring video after verification
with open('templates/student/exam.html', 'r') as f:
    content = f.read()

old = '''        // Start exam (hide verification overlay and show exam)
        // ONLY called after successful verification
        function startExam() {
            // Hide verification overlay completely
            document.getElementById('verification-overlay').style.display = 'none';
            
            // Show exam content
            document.getElementById('exam-content').style.display = 'flex';
            
            // Stop preview camera
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
        }'''

new = '''        // Start exam (hide verification overlay and show exam)
        // ONLY called after successful verification
        function startExam() {
            // Hide verification overlay completely
            document.getElementById('verification-overlay').style.display = 'none';
            
            // Show exam content
            document.getElementById('exam-content').style.display = 'flex';
            
            // Show proctoring video panel and start the video feed
            document.getElementById('proctoring-panel').style.display = 'block';
            document.getElementById('proctoring-video').src = "{{ url_for('video_feed') }}";
            
            // Stop preview camera
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
        }'''

content = content.replace(old, new)

with open('templates/student/exam.html', 'w') as f:
    f.write(content)

print('File updated successfully')
