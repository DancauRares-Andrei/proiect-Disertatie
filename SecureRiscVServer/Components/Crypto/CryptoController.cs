using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Numerics;
using System.Security.Claims;

namespace SecureRiscVServer.Components.Crypto
{
    [ApiController]
    [Route("api/crypto")]
    public class CryptoController : ControllerBase
    {
        private readonly SessionStore _sessions;
        private readonly AesService _aes;

        // o singură pereche RSA pentru server
        private static readonly RSA rsa = new();

        public CryptoController(SessionStore sessions, AesService aes)
        {
            _sessions = sessions;
            _aes = aes;
            rsa.GenerateKeys(1024);
        }

        // ======================
        // RSA public key
        // ======================
        [HttpGet("publickey")]
        public IActionResult GetPublicKey()
        {
            var (e, n) = rsa.PublicKey;
            return Ok(new
            {
                e = e.ToString(),
                n = n.ToString()
            });
        }

        // ======================
        // Handshake RSA → AES
        // ======================
        [Authorize]
        [HttpPost("handshake")]
        public IActionResult Handshake([FromBody] HandshakeRequest request)
        {
            if (request?.EncryptedKey == null || request.EncryptedKey.Count == 0)
                return BadRequest("EncryptedKey missing");

            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (userId == null)
                return Unauthorized();

            // Converting to BigInteger
            var cipher = request.EncryptedKey.ConvertAll(BigInteger.Parse);

            Console.WriteLine("=== Handshake DEBUG ===");
            Console.WriteLine("Cipher received:");
            foreach (var c in cipher)
                Console.WriteLine(c);

            // Decrypt
            byte[] decrypted = rsa.Decrypt(cipher[0]); // folosim primul BigInteger dacă trimitem ca un singur int

            Console.WriteLine("Decrypted bytes length: " + decrypted.Length);
            Console.WriteLine("Decrypted bytes: " + BitConverter.ToString(decrypted));

            if (decrypted.Length < 48)
                return BadRequest("Invalid key payload");

            var aesKey = decrypted[..32];
            var iv = decrypted[32..48];

            Console.WriteLine("AES Key: " + BitConverter.ToString(aesKey));
            Console.WriteLine("IV: " + BitConverter.ToString(iv));

            var session = new SecureSession
            {
                AesKey = aesKey,
                Iv = iv
            };

            _sessions.Set(userId, session);

            Console.WriteLine("Handshake completed for user: " + userId);
            return Ok("Handshake completed");
        }




        // ======================
        // Send AES-encrypted data
        // ======================
        [Authorize]
        [HttpPost("send")]
        public IActionResult SendSecureMessage([FromBody] SecureMessageRequest request)
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (userId == null)
                return Unauthorized();

            var session = _sessions.Get(userId);
            if (session == null)
                return BadRequest("No AES session. Perform handshake first.");

            byte[] encrypted = _aes.Encrypt(
                request.PlainText,
                session.AesKey,
                session.Iv
            );

            return Ok(new SecureMessageResponse
            {
                CipherText = Convert.ToBase64String(encrypted)
            });
        }
    }
}
