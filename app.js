document.addEventListener('DOMContentLoaded', () => {
    // --- BÖLÜM VE MENÜ YÖNETİMİ ---
    const menuCreateExam = document.getElementById('menu-create-exam');
    const menuClasses = document.getElementById('menu-classes');
    
    const sectionCreateExam = document.getElementById('section-create-exam');
    const sectionClasses = document.getElementById('section-classes');
    const pageTitle = document.getElementById('pageTitle');
    const pageDesc = document.getElementById('pageDesc');

    // Menü Değiştirme Fonksiyonu
    function switchTab(tab) {
        document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
        sectionCreateExam.classList.add('hidden');
        sectionClasses.classList.add('hidden');

        if(tab === 'create') {
            menuCreateExam.classList.add('active');
            sectionCreateExam.classList.remove('hidden');
            pageTitle.innerText = "Yeni Sınav Oluştur";
            pageDesc.innerText = "MEB müfredatına uygun yapay zeka destekli sorular.";
        } else if(tab === 'classes') {
            menuClasses.classList.add('active');
            sectionClasses.classList.remove('hidden');
            pageTitle.innerText = "Sınıflarım & Öğrenciler";
            pageDesc.innerText = "Sınıflarınızı oluşturun, kodları paylaşın ve öğrencilerinizi yönetin.";
            loadClasses(); // Sınıfları veritabanından çek
        }
    }

    menuCreateExam.addEventListener('click', (e) => { e.preventDefault(); switchTab('create'); });
    menuClasses.addEventListener('click', (e) => { e.preventDefault(); switchTab('classes'); });


    // --- SINIF OLUŞTURMA VE YÖNETİMİ ---
    const newClassNameInput = document.getElementById('newClassName');
    const createClassBtn = document.getElementById('createClassBtn');
    const classesList = document.getElementById('classesList');
    const targetClassSelect = document.getElementById('targetClassSelect');

    // Rastgele sınıf kodu üretici (Örn: 9A-XYZ)
    function generateClassCode(className) {
        const prefix = className.replace(/[^a-zA-Z0-9]/g, '').substring(0, 2).toUpperCase() || 'SN';
        const randomStr = Math.random().toString(36).substring(2, 6).toUpperCase();
        return `${prefix}-${randomStr}`;
    }

    // Sınıf Oluştur Butonu
    createClassBtn.addEventListener('click', async () => {
        const className = newClassNameInput.value.trim();
        if(!className) return alert("Lütfen sınıf adını girin.");
        
        const user = firebase.auth().currentUser;
        if(!user) return;

        createClassBtn.disabled = true;
        createClassBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Oluşturuluyor...';

        const classCode = generateClassCode(className);
        
        try {
            await db.collection("classes").add({
                name: className,
                code: classCode,
                teacherId: user.uid,
                createdAt: firebase.firestore.FieldValue.serverTimestamp(),
                students: []
            });
            
            newClassNameInput.value = '';
            alert(`Sınıf oluşturuldu! Sınıf Kodunuz: ${classCode}`);
            loadClasses(); // Listeyi yenile
        } catch (error) {
            console.error(error);
            alert("Sınıf oluşturulurken hata oluştu.");
        } finally {
            createClassBtn.disabled = false;
            createClassBtn.innerHTML = '<i class="fa-solid fa-plus"></i> Sınıf Oluştur';
        }
    });

    // Sınıfları Veritabanından Çek
    async function loadClasses() {
        const user = firebase.auth().currentUser;
        if(!user) return;

        try {
            const snapshot = await db.collection("classes").where("teacherId", "==", user.uid).get();
            classesList.innerHTML = '';
            targetClassSelect.innerHTML = '<option value="">Sınıf Seçin...</option>';
            
            if (snapshot.empty) {
                classesList.innerHTML = `
                    <div style="text-align: center; color: var(--text-muted); margin-top: 50px;">
                        <i class="fa-solid fa-users-slash" style="font-size: 3rem; margin-bottom: 10px;"></i>
                        <p>Henüz bir sınıf oluşturmadınız.</p>
                    </div>`;
                return;
            }

            snapshot.forEach(doc => {
                const data = doc.data();
                
                // Seçim kutusuna (Sınav Gönderme için) ekle
                const option = document.createElement('option');
                option.value = doc.id;
                option.innerText = data.name;
                targetClassSelect.appendChild(option);

                // Sınıflar listesine kart olarak ekle
                const card = document.createElement('div');
                card.style.cssText = "background: rgba(15,23,42,0.4); border: 1px solid var(--glass-border); padding: 15px; border-radius: 12px; margin-bottom: 15px; display: flex; flex-direction: column;";
                card.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="color: white; margin-bottom: 5px; font-size: 1.1rem;">${data.name}</h4>
                            <p style="color: var(--primary); font-family: monospace; font-size: 1.1rem;">
                                <i class="fa-solid fa-key"></i> ${data.code}
                            </p>
                            <p style="color: var(--text-muted); font-size: 0.8rem; margin-top: 5px;">
                                ${data.students ? data.students.length : 0} Öğrenci Katıldı
                            </p>
                        </div>
                        <div style="display: flex; gap: 10px;">
                            <button class="btn-primary" style="padding: 8px 15px;" onclick="loadResults('${doc.id}')">
                                <i class="fa-solid fa-chart-bar"></i> Karneler
                            </button>
                            <button class="btn-outline" style="padding: 8px 15px; border-color: #ef4444; color: #ef4444;" onclick="deleteClass('${doc.id}')">
                                <i class="fa-solid fa-trash"></i> Sil
                            </button>
                        </div>
                    </div>
                    <div id="results-${doc.id}" style="margin-top: 15px; display: none; border-top: 1px solid var(--glass-border); padding-top: 15px;">
                        <!-- Sonuçlar Buraya Gelecek -->
                    </div>
                `;
                classesList.appendChild(card);
            });
        } catch (error) {
            console.error("Sınıflar yüklenemedi:", error);
        }
    }

    // Karneleri (Sonuçları) Yükleme Fonksiyonu
    window.loadResults = async (classId) => {
        const resultsContainer = document.getElementById(`results-${classId}`);
        
        // Kapat/Aç mantığı (Toggle)
        if(resultsContainer.style.display === 'block') {
            resultsContainer.style.display = 'none';
            return;
        }
        
        resultsContainer.style.display = 'block';
        resultsContainer.innerHTML = '<div style="color: var(--primary);"><i class="fa-solid fa-spinner fa-spin"></i> Veriler getiriliyor...</div>';

        try {
            // Sınıfa ait sınavları bul
            const examsSnap = await db.collection("exams").where("classId", "==", classId).get();
            if(examsSnap.empty) {
                resultsContainer.innerHTML = '<p style="color: var(--text-muted);">Bu sınıfa henüz sınav gönderilmemiş.</p>';
                return;
            }

            let examsHTML = '';
            
            // Her sınav için döngü
            for(let examDoc of examsSnap.docs) {
                const exam = examDoc.data();
                
                // Bu sınavın sonuçlarını bul
                const resultsSnap = await db.collection("results").where("examId", "==", examDoc.id).get();
                
                let studentResultsHTML = '';
                if(resultsSnap.empty) {
                    studentResultsHTML = '<p style="color: #94a3b8; font-size: 0.8rem; margin-top: 5px;">Henüz hiçbir öğrenci çözmemiş.</p>';
                } else {
                    resultsSnap.forEach(resDoc => {
                        const res = resDoc.data();
                        let badgeColor = res.score >= 80 ? 'var(--success)' : (res.score >= 50 ? '#f59e0b' : '#ef4444');
                        studentResultsHTML += `
                            <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.2); padding: 8px 12px; border-radius: 6px; margin-top: 5px;">
                                <span style="color: #cbd5e1; font-size: 0.9rem;">${res.studentEmail.split('@')[0]}</span>
                                <span style="color: ${badgeColor}; font-weight: bold; font-size: 0.9rem;">${res.score} Puan</span>
                            </div>
                        `;
                    });
                }

                examsHTML += `
                    <div style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); padding: 12px; border-radius: 8px; margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <h5 style="color: white; margin: 0;">
                                <i class="fa-solid fa-file-lines" style="color: var(--primary);"></i> ${exam.title}
                            </h5>
                            <button class="btn-primary" style="padding: 4px 10px; font-size: 0.8rem; margin: 0; width: auto;" onclick="openExamReport('${examDoc.id}', '${classId}')">
                                Detaylı Rapor <i class="fa-solid fa-arrow-up-right-from-square"></i>
                            </button>
                        </div>
                        ${studentResultsHTML}
                    </div>
                `;
            }

            resultsContainer.innerHTML = examsHTML;

        } catch (error) {
            console.error("Sonuçlar getirilemedi:", error);
            resultsContainer.innerHTML = '<p style="color: #ef4444;">Sonuçlar yüklenirken hata oluştu.</p>';
        }
    };

    // Detaylı Raporlama Modalını Açan Fonksiyon
    window.openExamReport = async (examId, classId) => {
        const modal = document.getElementById('reportModal');
        modal.style.display = 'flex';
        
        document.getElementById('reportAvgScore').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        document.getElementById('reportParticipation').innerHTML = '-';
        document.getElementById('hardestQuestionsList').innerHTML = '';
        document.getElementById('studentAnalysisList').innerHTML = '';

        try {
            const classDoc = await db.collection("classes").doc(classId).get();
            const examDoc = await db.collection("exams").doc(examId).get();
            const resultsSnap = await db.collection("results").where("examId", "==", examId).get();

            const classData = classDoc.data();
            const examData = examDoc.data();
            const questions = examData.questions;
            const totalStudents = classData.students ? classData.students.length : 0;
            const participantCount = resultsSnap.size;

            document.getElementById('reportModalTitle').innerText = `${examData.title} Raporu (${classData.name})`;

            if (participantCount === 0) {
                document.getElementById('reportAvgScore').innerText = "0";
                document.getElementById('reportParticipation').innerText = `0 / ${totalStudents}`;
                document.getElementById('hardestQuestionsList').innerHTML = '<p style="color: var(--text-muted);">Henüz katılım yok.</p>';
                return;
            }

            let totalScore = 0;
            let wrongCountsArray = new Array(questions.length).fill(0); // Her sorunun kaç kez yanlış yapıldığını tutar
            let studentAnalysisHTML = '';

            resultsSnap.forEach(resDoc => {
                const res = resDoc.data();
                totalScore += res.score;

                let studentWrongList = [];

                // Öğrencinin cevaplarını kontrol et
                res.userAnswers.forEach((answer, qIndex) => {
                    const isCorrect = answer === questions[qIndex].dogru_cevap;
                    if (!isCorrect) {
                        wrongCountsArray[qIndex]++;
                        studentWrongList.push(`Soru ${qIndex + 1}`);
                    }
                });

                let badgeColor = res.score >= 80 ? 'var(--success)' : (res.score >= 50 ? '#f59e0b' : '#ef4444');
                studentAnalysisHTML += `
                    <div style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong style="color: white;">${res.studentEmail}</strong>
                            <span style="color: ${badgeColor}; font-weight: bold;">${res.score} Puan</span>
                        </div>
                        ${studentWrongList.length > 0 ? `<p style="color: #ef4444; font-size: 0.85rem; margin-top: 5px; margin-bottom: 0;">Yanlışları: ${studentWrongList.join(', ')}</p>` : `<p style="color: var(--success); font-size: 0.85rem; margin-top: 5px; margin-bottom: 0;">Tüm soruları doğru bildi!</p>`}
                    </div>
                `;
            });

            // Ortalamaları yazdır
            const avgScore = Math.round(totalScore / participantCount);
            document.getElementById('reportAvgScore').innerText = avgScore;
            document.getElementById('reportAvgScore').style.color = avgScore >= 80 ? 'var(--success)' : (avgScore >= 50 ? '#f59e0b' : '#ef4444');
            document.getElementById('reportParticipation').innerText = `${participantCount} / ${totalStudents}`;

            // En zor soruları bul (Yanlış yapılma sayısına göre)
            let hardestQuestionsHTML = '';
            let hasWrongQuestions = false;

            wrongCountsArray.forEach((wrongCount, qIndex) => {
                if (wrongCount > 0) {
                    hasWrongQuestions = true;
                    // Yanlış yapılma oranı
                    const wrongPercentage = Math.round((wrongCount / participantCount) * 100);
                    hardestQuestionsHTML += `
                        <div style="background: rgba(245, 158, 11, 0.1); border-left: 3px solid #f59e0b; padding: 12px; margin-bottom: 10px; border-radius: 4px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                <strong style="color: white;">Soru ${qIndex + 1}</strong>
                                <span style="color: #f59e0b; font-size: 0.9rem;">Sınıfın %${wrongPercentage}'i yanlış yaptı</span>
                            </div>
                            <p style="color: #94a3b8; font-size: 0.85rem; margin: 0;">${questions[qIndex].soru.substring(0, 100)}...</p>
                        </div>
                    `;
                }
            });

            if(!hasWrongQuestions) {
                hardestQuestionsHTML = '<p style="color: var(--success);"><i class="fa-solid fa-check"></i> Sınıftaki herkes tüm soruları doğru cevaplamış!</p>';
            }

            document.getElementById('hardestQuestionsList').innerHTML = hardestQuestionsHTML;
            document.getElementById('studentAnalysisList').innerHTML = studentAnalysisHTML;

        } catch (error) {
            console.error("Rapor oluşturulamadı:", error);
            alert("Rapor oluşturulurken bir hata meydana geldi.");
            modal.style.display = 'none';
        }
    };

    // Modal Kapatma
    const closeModalBtn = document.getElementById('closeModalBtn');
    if(closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            document.getElementById('reportModal').style.display = 'none';
        });
    }

    // Global fonksiyon (Sınıf Silme)
    window.deleteClass = async (classId) => {
        if(confirm("Bu sınıfı silmek istediğinize emin misiniz? Öğrenciler de bu sınıftan çıkarılacaktır.")) {
            try {
                await db.collection("classes").doc(classId).delete();
                loadClasses();
            } catch (error) {
                console.error("Silinemedi:", error);
            }
        }
    };

    // Firebase Auth hazır olduğunda sınıfları arka planda yükle
    firebase.auth().onAuthStateChanged(user => {
        if(user) loadClasses();
    });


    // --- SINAV OLUŞTURMA VE GÖNDERME ---
    const generateBtn = document.getElementById('generateBtn');
    const statusArea = document.getElementById('statusArea');
    const loadingArea = document.getElementById('loadingArea');
    const resultArea = document.getElementById('resultArea');
    const progressBar = document.getElementById('progressBar');
    const loadingText = document.getElementById('loadingText');
    const examPreviewContent = document.getElementById('examPreviewContent');
    const assignToClassBtn = document.getElementById('assignToClassBtn');

    let generatedExamData = null; // Üretilen sınavı hafızada tut

    generateBtn.addEventListener('click', async () => {
        const grade = document.getElementById('grade').value;
        const subject = document.getElementById('subject').options[document.getElementById('subject').selectedIndex].text;
        const unitText = document.getElementById('unit').options[document.getElementById('unit').selectedIndex].text;
        const qCount = parseInt(document.getElementById('questionCount').value);

        statusArea.classList.add('hidden');
        resultArea.classList.add('hidden');
        loadingArea.classList.remove('hidden');
        
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Hazırlanıyor...';
        progressBar.style.width = '30%';
        loadingText.innerText = "Yapay Zeka kitapları okuyor ve soruları üretiyor...";

        try {
            let data = null;

            // 1. Önce Veritabanı Havuzunda (Cache) bu sorular var mı kontrol et
            const cacheSnapshot = await db.collection("questionBank")
                .where("grade", "==", grade)
                .where("subject", "==", subject)
                .where("unit", "==", unitText)
                .where("count", "==", qCount)
                .limit(1)
                .get();

            if (!cacheSnapshot.empty) {
                // Havuzda bulundu! Hızlıca getir.
                console.log("Sorular veritabanı havuzundan (cache) getirildi.");
                data = {
                    success: true,
                    questions: cacheSnapshot.docs[0].data().questions
                };
            } else {
                // Havuzda yoksa yapay zekaya sor
                console.log("Sorular havuzda bulunamadı, yapay zekaya istek atılıyor...");
                
                // Canlı ortam veya lokal ortam için dinamik API adresi (HTTPS güvenliği için)
                const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
                const API_BASE_URL = isLocal ? 'http://127.0.0.1:5000' : 'https://senin-python-sunucun-adresi.com';

                const response = await fetch(`${API_BASE_URL}/generate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ grade, subject, unit: unitText, count: qCount })
                });

                data = await response.json();

                if (data.success) {
                    // Üretilen soruları gelecekteki kullanımlar için havuza kaydet
                    await db.collection("questionBank").add({
                        grade: grade,
                        subject: subject,
                        unit: unitText,
                        count: qCount,
                        questions: data.questions,
                        createdAt: firebase.firestore.FieldValue.serverTimestamp()
                    });
                }
            }

            if (data.success) {
                progressBar.style.width = '100%';
                loadingText.innerText = "Sorular başarıyla üretildi!";
                
                generatedExamData = {
                    title: `${grade}. Sınıf ${subject} - ${unitText.split(':')[1] || unitText}`,
                    questions: data.questions,
                    createdAt: firebase.firestore.FieldValue.serverTimestamp(),
                    teacherId: firebase.auth().currentUser.uid
                };
                
                // Önizlemeyi Oluştur
                examPreviewContent.innerHTML = '';
                data.questions.forEach((q, index) => {
                    let optionsHTML = '';
                    q.secenekler.forEach(opt => {
                        const isCorrect = opt.startsWith(q.dogru_cevap);
                        const optColor = isCorrect ? 'color: var(--success); font-weight: bold;' : 'color: var(--text-muted);';
                        optionsHTML += `<div style="${optColor} margin-bottom: 5px;">${opt} ${isCorrect ? '<i class="fa-solid fa-check"></i>' : ''}</div>`;
                    });

                    examPreviewContent.innerHTML += `
                        <div style="background: rgba(0,0,0,0.2); padding: 15px; border-radius: 12px; margin-bottom: 15px; border: 1px solid var(--glass-border);">
                            <h4 style="color: white; margin-bottom: 10px;">Soru ${index + 1}: ${q.soru}</h4>
                            <div style="margin-left: 10px;">
                                ${optionsHTML}
                            </div>
                        </div>
                    `;
                });
                
                setTimeout(() => {
                    loadingArea.classList.add('hidden');
                    resultArea.classList.remove('hidden');
                    generateBtn.disabled = false;
                    generateBtn.innerHTML = '<i class="fa-solid fa-robot"></i> Yeni Sınav Oluştur';
                }, 1000);
            } else {
                alert("Hata: " + data.error);
                resetUI();
            }
        } catch (error) {
            console.error(error);
            alert("Sunucuya bağlanılamadı. 'python server.py' çalışıyor mu?");
            resetUI();
        }
    });

    function resetUI() {
        loadingArea.classList.add('hidden');
        statusArea.classList.remove('hidden');
        generateBtn.disabled = false;
        generateBtn.innerHTML = '<i class="fa-solid fa-robot"></i> Sınavı Oluştur';
    }

    // Sınıfa Gönder Butonu
    assignToClassBtn.addEventListener('click', async () => {
        const classId = targetClassSelect.value;
        if(!classId) return alert("Lütfen sınavı göndermek için bir sınıf seçin!");
        if(!generatedExamData) return alert("Gönderilecek sınav bulunamadı.");

        assignToClassBtn.disabled = true;
        assignToClassBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Gönderiliyor...';

        try {
            // Sınava classId'yi ekle
            const examToSave = {
                ...generatedExamData,
                classId: classId
            };
            
            await db.collection("exams").add(examToSave);
            
            alert("Sınav başarıyla sınıfa gönderildi!");
            assignToClassBtn.innerHTML = '<i class="fa-solid fa-check"></i> Gönderildi';
            assignToClassBtn.style.background = 'var(--success)';
            
            setTimeout(() => {
                assignToClassBtn.disabled = false;
                assignToClassBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Sınıfa Gönder';
                assignToClassBtn.style.background = 'var(--primary)';
            }, 3000);

        } catch (error) {
            console.error("Sınav gönderilirken hata:", error);
            alert("Sınav gönderilemedi.");
            assignToClassBtn.disabled = false;
            assignToClassBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Sınıfa Gönder';
        }
    });
});
