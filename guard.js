// Firebase Config
const firebaseConfig = {
  apiKey: "AIzaSyC2p1uvYNF75Q6va5H_eRBm_MNfrxN4lyU",
  authDomain: "eduai-sinav.firebaseapp.com",
  projectId: "eduai-sinav",
  storageBucket: "eduai-sinav.firebasestorage.app",
  messagingSenderId: "663810168320",
  appId: "1:663810168320:web:3cce078ce22641d54f6ae5",
  measurementId: "G-9H49Z6Y8FN"
};

// Initialize Firebase (Compat)
if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
}

const db = firebase.firestore();

// Auth Guard: Güvenli Rol Kontrolü
firebase.auth().onAuthStateChanged(async (user) => {
    if (!user) {
        window.location.href = "login.html";
        return;
    }

    try {
        const doc = await db.collection("users").doc(user.uid).get();
        if (doc.exists) {
            const role = doc.data().role;
            const currentPath = window.location.pathname;

            // Eğer ana sayfadaysa (index.html), direkt rolüne göre yönlendir
            if (currentPath.includes('index.html') || currentPath.endsWith('/otomatik-sinav-asistani/')) {
                window.location.href = role === 'teacher' ? "teacher.html" : "student.html";
                return;
            }

            // Öğrenci yanlışlıkla teacher.html'ye girmeye çalışıyorsa
            if (role === 'student' && currentPath.includes('teacher.html')) {
                window.location.href = "student.html";
                return;
            }
            // Öğretmen yanlışlıkla student.html'ye girmeye çalışıyorsa
            if (role === 'teacher' && currentPath.includes('student.html')) {
                window.location.href = "teacher.html";
                return;
            }

            // Ekrana bilgileri yaz
            const userEmailEl = document.getElementById('userEmailDisplay');
            if(userEmailEl) userEmailEl.innerText = user.email;

            const roleDisplayEl = document.getElementById('userRoleDisplay');
            if(roleDisplayEl) {
                roleDisplayEl.innerText = role === 'teacher' ? 'Öğretmen' : 'Öğrenci';
            }
        } else {
            // Eğer Firebase Auth'da oturum açık ama Firestore'da rolü yoksa (eski veya hatalı hesap)
            console.error("Kullanıcının veritabanında kaydı bulunamadı.");
            firebase.auth().signOut().then(() => {
                window.location.href = "login.html";
            });
        }
    } catch (error) {
        console.error("Yetki kontrolünde hata:", error);
        // Hata durumunda da login ekranına at ki ekranda donup kalmasın
        window.location.href = "login.html";
    }
});

// Çıkış Yap Butonu
const logoutBtn = document.getElementById('logoutBtn');
if(logoutBtn) {
    logoutBtn.addEventListener('click', () => {
        firebase.auth().signOut().then(() => {
            window.location.href = "login.html";
        }).catch((error) => {
            console.error("Çıkış hatası:", error);
        });
    });
}
