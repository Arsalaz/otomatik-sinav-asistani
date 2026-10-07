document.addEventListener('DOMContentLoaded', () => {
    // --- BÖLÜM VE MENÜ YÖNETİMİ ---
    const menuJoinClass = document.getElementById('menu-join-class');
    const menuMyClasses = document.getElementById('menu-my-classes');
    
    const sectionJoinClass = document.getElementById('section-join-class');
    const sectionMyClasses = document.getElementById('section-my-classes');
    const pageTitle = document.getElementById('pageTitle');
    const pageDesc = document.getElementById('pageDesc');

    // Menü Değiştirme Fonksiyonu
    function switchTab(tab) {
        document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
        sectionJoinClass.classList.add('hidden');
        sectionMyClasses.classList.add('hidden');

        if(tab === 'join') {
            menuJoinClass.classList.add('active');
            sectionJoinClass.classList.remove('hidden');
            pageTitle.innerText = "Merhaba, Öğrenci! 👋";
            pageDesc.innerText = "Buradan sınıflarına katılabilir ve sana atanan sınavları görebilirsin.";
        } else if(tab === 'classes') {
            menuMyClasses.classList.add('active');
            sectionMyClasses.classList.remove('hidden');
            pageTitle.innerText = "Sınıflarım";
            pageDesc.innerText = "Katıldığın sınıfları ve bekleyen sınavları aşağıdan görebilirsin.";
            loadMyClassesAndExams(); // Sınıfları ve sınavları veritabanından çek
        }
    }

    menuJoinClass.addEventListener('click', (e) => { e.preventDefault(); switchTab('join'); });
    menuMyClasses.addEventListener('click', (e) => { e.preventDefault(); switchTab('classes'); });

    // --- SINIFA KATILMA İŞLEMİ ---
    const classCodeInput = document.getElementById('classCode');
    const joinClassBtn = document.getElementById('joinClassBtn');

    joinClassBtn.addEventListener('click', async () => {
        const code = classCodeInput.value.trim().toUpperCase();
        if(!code) return alert("Lütfen bir sınıf kodu girin.");

        const user = firebase.auth().currentUser;
        if(!user) return alert("Lütfen giriş yapın.");

        joinClassBtn.disabled = true;
        joinClassBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Aranıyor...';

        try {
            // Sınıf kodunu veritabanında ara
            const snapshot = await db.collection("classes").where("code", "==", code).get();
            
            if(snapshot.empty) {
                alert("Böyle bir sınıf bulunamadı. Kodu kontrol edip tekrar deneyin.");
                joinClassBtn.disabled = false;
                joinClassBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Sınıfa Katıl';
                return;
            }

            const classDoc = snapshot.docs[0];
            const classData = classDoc.data();
            
            // Zaten bu sınıftaysa uyar
            const alreadyJoined = classData.students && classData.students.find(s => s.uid === user.uid);
            if(alreadyJoined) {
                alert("Zaten bu sınıfa kayıtlısınız!");
                classCodeInput.value = '';
                joinClassBtn.disabled = false;
                joinClassBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Sınıfa Katıl';
                return;
            }

            // Sınıf bulunduysa öğrenciyi listeye ekle
            await db.collection("classes").doc(classDoc.id).update({
                students: firebase.firestore.FieldValue.arrayUnion({
                    uid: user.uid,
                    email: user.email,
                    joinedAt: new Date()
                })
            });

            alert(`Başarılı! '${classData.name}' sınıfına katıldınız.`);
            classCodeInput.value = '';
            
            joinClassBtn.innerHTML = '<i class="fa-solid fa-check"></i> Katıldınız';
            joinClassBtn.style.background = 'var(--success)';
            
            setTimeout(() => {
                joinClassBtn.disabled = false;
                joinClassBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Sınıfa Katıl';
                joinClassBtn.style.background = 'var(--primary)';
                switchTab('classes'); // Başarılı olunca sınıflarım sekmesine geç
            }, 2000);

        } catch (error) {
            console.error("Sınıfa katılırken hata:", error);
            alert("Bir hata oluştu, lütfen tekrar deneyin.");
            joinClassBtn.disabled = false;
            joinClassBtn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Sınıfa Katıl';
        }
    });

    // --- SINIFLARI VE SINAVLARI GETİR ---
    const myClassesList = document.getElementById('myClassesList');

    async function loadMyClassesAndExams() {
        const user = firebase.auth().currentUser;
        if(!user) return;

        myClassesList.innerHTML = '<div style="text-align: center;"><i class="fa-solid fa-spinner fa-spin" style="font-size: 2rem; color: var(--primary);"></i></div>';

        try {
            // Öğrencinin (user.uid) içinde bulunduğu sınıfları getir (Dizide obje aramak zor olduğu için tüm sınıfları çekip filtreleyeceğiz)
            const classesSnapshot = await db.collection("classes").get();
            let myClasses = [];
            
            classesSnapshot.forEach(doc => {
                const data = doc.data();
                if(data.students && data.students.some(s => s.uid === user.uid)) {
                    myClasses.push({ id: doc.id, ...data });
                }
            });

            if (myClasses.length === 0) {
                myClassesList.innerHTML = `
                    <div style="text-align: center; color: var(--text-muted); margin-top: 50px;">
                        <i class="fa-solid fa-folder-open" style="font-size: 3rem; margin-bottom: 10px;"></i>
                        <p>Henüz hiçbir sınıfa kayıtlı değilsiniz.</p>
                    </div>`;
                return;
            }

            myClassesList.innerHTML = ''; // Temizle

            // Sınıfları ekrana çiz
            for (let cls of myClasses) {
                const classCard = document.createElement('div');
                classCard.style.cssText = "background: rgba(15,23,42,0.4); border: 1px solid var(--glass-border); padding: 20px; border-radius: 12px; margin-bottom: 20px;";
                
                // Başlık kısmı
                classCard.innerHTML = `
                    <div style="border-bottom: 1px solid var(--glass-border); padding-bottom: 10px; margin-bottom: 15px;">
                        <h4 style="color: white; font-size: 1.2rem; margin: 0;">
                            <i class="fa-solid fa-chalkboard-user" style="color: var(--primary);"></i> ${cls.name}
                        </h4>
                    </div>
                    <div class="exams-container" id="exams-${cls.id}">
                        <div style="color: var(--text-muted); font-size: 0.9rem;"><i class="fa-solid fa-spinner fa-spin"></i> Sınavlar kontrol ediliyor...</div>
                    </div>
                `;
                
                myClassesList.appendChild(classCard);

                // Bu sınıfa ait sınavları çek
                const examsSnapshot = await db.collection("exams").where("classId", "==", cls.id).get();
                const examsContainer = document.getElementById(`exams-${cls.id}`);
                
                if (examsSnapshot.empty) {
                    examsContainer.innerHTML = '<p style="color: var(--text-muted); font-size: 0.9rem;">Bu sınıfa henüz bir sınav atanmamış.</p>';
                } else {
                    examsContainer.innerHTML = '';
                    for (let examDoc of examsSnapshot.docs) {
                        const exam = examDoc.data();
                        
                        // Öğrencinin daha önce bu sınavı çözüp çözmediğini kontrol et
                        const resultSnap = await db.collection("results")
                            .where("examId", "==", examDoc.id)
                            .where("studentId", "==", user.uid)
                            .get();
                            
                        const hasSolved = !resultSnap.empty;
                        let actionButtonHTML = '';
                        
                        if (hasSolved) {
                            const resData = resultSnap.docs[0].data();
                            actionButtonHTML = `
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <span style="color: var(--success); font-weight: bold; font-size: 1.1rem;">${resData.score} Puan</span>
                                    <button class="btn-outline" style="margin: 0; padding: 6px 15px; font-size: 0.9rem; border-color: var(--primary); color: var(--primary);" onclick="showReport('${examDoc.id}', '${resultSnap.docs[0].id}')">
                                        <i class="fa-solid fa-chart-bar"></i> Karnemi Gör
                                    </button>
                                </div>
                            `;
                        } else {
                            actionButtonHTML = `
                                <button class="btn-primary" style="margin: 0; padding: 6px 15px; font-size: 0.9rem;" onclick="startExam('${examDoc.id}')">
                                    <i class="fa-solid fa-play"></i> Çöz
                                </button>
                            `;
                        }

                        examsContainer.innerHTML += `
                            <div style="background: rgba(79, 70, 229, 0.1); border: 1px solid rgba(79, 70, 229, 0.3); padding: 12px 15px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <h5 style="color: white; margin-bottom: 3px;">${exam.title || 'İsimsiz Sınav'}</h5>
                                    <p style="color: #94a3b8; font-size: 0.8rem;">${exam.questions ? exam.questions.length : 0} Soru</p>
                                </div>
                                ${actionButtonHTML}
                            </div>
                        `;
                    }
                }
            }
        } catch (error) {
            console.error("Veriler yüklenemedi:", error);
            myClassesList.innerHTML = '<p style="color: #ef4444;">Veriler yüklenirken bir hata oluştu.</p>';
        }
    }

    // --- SINAV ÇÖZME VE KARNE MANTIĞI ---
    const sectionExam = document.getElementById('section-exam');
    const sectionReport = document.getElementById('section-report');
    
    // Sınav UI Elementleri
    const examTitle = document.getElementById('examTitle');
    const currentQNum = document.getElementById('currentQNum');
    const totalQNum = document.getElementById('totalQNum');
    const questionText = document.getElementById('questionText');
    const optionsContainer = document.getElementById('optionsContainer');
    const prevQBtn = document.getElementById('prevQBtn');
    const nextQBtn = document.getElementById('nextQBtn');
    const finishExamBtn = document.getElementById('finishExamBtn');
    
    // Karne UI Elementleri
    const finalScoreEl = document.getElementById('finalScore');
    const reportContent = document.getElementById('reportContent');
    const backToClassesBtn = document.getElementById('backToClassesBtn');

    let currentExamData = null;
    let currentQuestions = [];
    let userAnswers = [];
    let currentQuestionIndex = 0;
    let isExamActive = false; // Kopya kontrolü için sınav durumu

    window.startExam = async (examId) => {
        try {
            const doc = await db.collection("exams").doc(examId).get();
            if(!doc.exists) return alert("Sınav bulunamadı!");
            
            currentExamData = { id: doc.id, ...doc.data() };
            currentQuestions = currentExamData.questions;
            userAnswers = new Array(currentQuestions.length).fill(null);
            currentQuestionIndex = 0;

            document.getElementById('section-join-class').classList.add('hidden');
            document.getElementById('section-my-classes').classList.add('hidden');
            document.querySelector('.header').classList.add('hidden');
            sectionExam.classList.remove('hidden');

            examTitle.innerText = currentExamData.title || "Sınav";
            isExamActive = true; // Sınav başladı
            loadQuestion(0);
        } catch (error) {
            console.error(error);
            alert("Sınav yüklenirken hata oluştu.");
        }
    };

    function loadQuestion(index) {
        const q = currentQuestions[index];
        currentQNum.innerText = index + 1;
        totalQNum.innerText = currentQuestions.length;
        questionText.innerText = q.soru;
        
        optionsContainer.innerHTML = '';
        q.secenekler.forEach((opt) => {
            const btn = document.createElement('button');
            btn.className = 'option-btn';
            btn.innerText = opt;
            
            const letterMatch = opt.match(/^([A-D])\)/);
            const letter = letterMatch ? letterMatch[1] : opt.charAt(0);
            
            if (userAnswers[index] === letter) {
                btn.classList.add('selected');
            }
            
            btn.onclick = () => {
                document.querySelectorAll('.option-btn').forEach(b => b.classList.remove('selected'));
                btn.classList.add('selected');
                userAnswers[index] = letter;
            };
            optionsContainer.appendChild(btn);
        });

        prevQBtn.style.display = index > 0 ? 'inline-block' : 'none';
        
        if (index === currentQuestions.length - 1) {
            nextQBtn.style.display = 'none';
            finishExamBtn.style.display = 'inline-block';
        } else {
            nextQBtn.style.display = 'inline-block';
            finishExamBtn.style.display = 'none';
        }
    }

    nextQBtn.addEventListener('click', () => {
        if (currentQuestionIndex < currentQuestions.length - 1) {
            currentQuestionIndex++;
            loadQuestion(currentQuestionIndex);
        }
    });

    prevQBtn.addEventListener('click', () => {
        if (currentQuestionIndex > 0) {
            currentQuestionIndex--;
            loadQuestion(currentQuestionIndex);
        }
    });

    function renderReportContent(questions, answers, score) {
        let wrongQuestionsHTML = '';
        questions.forEach((q, index) => {
            const userAnswer = answers[index];
            const isCorrect = userAnswer === q.dogru_cevap;
            
            if (!isCorrect) {
                wrongQuestionsHTML += `
                    <div class="wrong-answer-card">
                        <h4>Soru ${index + 1}: ${q.soru}</h4>
                        <p style="color: #94a3b8; font-size: 0.9rem;">Senin Cevabın: <span style="color: #ef4444">${userAnswer || "Boş Bırakıldı"}</span></p>
                        <p class="correct-is">Doğru Cevap: ${q.dogru_cevap}</p>
                    </div>
                `;
            }
        });

        finalScoreEl.innerText = score;
        
        if (score === 100) {
            reportContent.innerHTML = `<div style="text-align:center; padding: 2rem;">
                <i class="fa-solid fa-trophy" style="font-size: 4rem; color: #ffd700; margin-bottom:1rem;"></i>
                <h3 style="color: white;">Tebrikler! Mükemmel Sonuç!</h3>
                <p style="color: #94a3b8;">Hiç eksiğin yok, bu üniteyi tam anlamıyla kavramışsın.</p>
            </div>`;
        } else {
            reportContent.innerHTML = wrongQuestionsHTML;
        }

        document.getElementById('section-join-class').classList.add('hidden');
        document.getElementById('section-my-classes').classList.add('hidden');
        document.querySelector('.header').classList.add('hidden');
        sectionExam.classList.add('hidden');
        sectionReport.classList.remove('hidden');
    }

    async function finishExam(isCheating = false) {
        if (!isExamActive) return;
        isExamActive = false; // Sınavı sonlandır

        let score = 0;
        let correctCount = 0;

        if (isCheating) {
            // Kopya çekenin puanı direkt 0 olur
            score = 0;
        } else {
            currentQuestions.forEach((q, index) => {
                if (userAnswers[index] === q.dogru_cevap) correctCount++;
            });
            score = Math.round((correctCount / currentQuestions.length) * 100);
        }
        
        // Sonucu veritabanına kaydet
        try {
            const user = firebase.auth().currentUser;
            if(user) {
                await db.collection("results").add({
                    examId: currentExamData.id,
                    studentId: user.uid,
                    studentEmail: user.email,
                    score: score,
                    cheated: isCheating,
                    userAnswers: userAnswers,
                    completedAt: firebase.firestore.FieldValue.serverTimestamp()
                });
            }
        } catch(error) {
            console.error("Sonuç kaydedilemedi:", error);
        }

        if (isCheating) {
            alert("⚠️ DİKKAT: Sınav sırasında sekme değiştirdiğiniz veya ekranı terk ettiğiniz için kopya çekme girişiminden dolayı sınavınız iptal edildi (0 puan).");
            sectionExam.classList.add('hidden');
            document.querySelector('.header').classList.remove('hidden');
            document.getElementById('menu-my-classes').click();
        } else {
            renderReportContent(currentQuestions, userAnswers, score);
        }
    }

    finishExamBtn.addEventListener('click', () => {
        finishExam(false);
    });

    // --- KOPYA KONTROLÜ (ANTI-CHEAT) ---
    document.addEventListener("visibilitychange", () => {
        if (isExamActive && document.visibilityState === 'hidden') {
            finishExam(true);
        }
    });

    window.addEventListener("blur", () => {
        if (isExamActive) {
            finishExam(true);
        }
    });

    window.showReport = async (examId, resultId) => {
        try {
            // Sınav sorularını ve sonucunu veritabanından çek
            const examDoc = await db.collection("exams").doc(examId).get();
            const resultDoc = await db.collection("results").doc(resultId).get();

            if(examDoc.exists && resultDoc.exists) {
                const examData = examDoc.data();
                const resultData = resultDoc.data();
                
                renderReportContent(examData.questions, resultData.userAnswers, resultData.score);
            }
        } catch(error) {
            console.error("Karne yüklenemedi:", error);
            alert("Karne yüklenirken bir hata oluştu.");
        }
    };

    backToClassesBtn.addEventListener('click', () => {
        sectionReport.classList.add('hidden');
        document.querySelector('.header').classList.remove('hidden');
        // switchTab yerine manuel class listesi güncelleme tetikleyelim ki çözülenler Karnemi Gör'e dönsün
        document.getElementById('menu-my-classes').click();
    });
});
