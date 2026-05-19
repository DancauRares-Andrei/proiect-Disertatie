using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SecureRiscVServer.Data;
using SecureRiscVServer.Service;
using System.Numerics;
using System.Security.Claims;
using System.Text;

namespace SecureRiscVServer.Controller
{
    [ApiController]
    [Route("api/crypto")]
    public class CryptoController : ControllerBase
    {
        private readonly SessionStore _sessions;
        private readonly AESService _aes;
        private readonly InstructionQueue _instructionQueue;

        private static readonly RSAService rsa = new();

        public CryptoController(SessionStore sessions, AESService aes, InstructionQueue instructionQueue)
        {
            _sessions = sessions;
            _aes = aes;
            _instructionQueue = instructionQueue;
            if (rsa.PublicKey.n == 0)
                rsa.GenerateKeys(1024);
        }

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

        [Authorize]
        [HttpPost("handshake")]
        public IActionResult Handshake([FromBody] HandshakeRequest request)
        {
            if (request?.EncryptedKey == null || request.EncryptedKey.Count != 1)
                return BadRequest("Format incorect pentru cheie!");

            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (userId == null)
                return Unauthorized();

            BigInteger c = BigInteger.Parse(request.EncryptedKey[0]);

            byte[] decryptedFull = rsa.Decrypt(c); 

            // Extragere cheie si iv 16 octeti cheie AES key + 16 octeti IV
            if (decryptedFull.Length < 32)
                return BadRequest("Date AES invalide!");

            byte[] decrypted = decryptedFull[^32..];

            var session = new SecureSession
            {
                AesKey = decrypted[..16],
                Iv = decrypted[16..32]
            };

            _sessions.Set(userId, session);

            Console.WriteLine($"[Handshake] OK pentru {userId}");
            Console.WriteLine($"Cheie AES: {BitConverter.ToString(session.AesKey)}");
            Console.WriteLine($"IV:      {BitConverter.ToString(session.Iv)}");

            return Ok();
        }

        [Authorize]
        [HttpGet("program")]
        public IActionResult GetProgram()
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (userId == null)
                return Unauthorized();

            var session = _sessions.Get(userId);
            if (session == null)
                return BadRequest("Nu este definita sesiune!");

            var instructions = _instructionQueue.GetAll(userId);

            if (instructions.Count == 0)
                return NoContent();

            byte[] payload = new byte[instructions.Count * 4];
            for (int i = 0; i < instructions.Count; i++)
            {
                Array.Copy(
                    BitConverter.GetBytes(instructions[i]),
                    0,
                    payload,
                    i * 4,
                    4
                );
            }

            byte[] encrypted = _aes.Encrypt(payload, session.AesKey, session.Iv);
            _instructionQueue.Clear(userId);
            return Ok(Convert.ToBase64String(encrypted));
        }

        [Authorize]
        [HttpPost("program")]
        public IActionResult PostProgram([FromBody] InstructionUploadRequest request)
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (userId == null)
                return Unauthorized();

            if (request?.Instructions == null || request.Instructions.Count == 0)
                return BadRequest("Nu au fost furnizate instructiuni!");

            var parsed = new List<uint>();

            foreach (var s in request.Instructions)
            {
                var clean = s.StartsWith("0x", StringComparison.OrdinalIgnoreCase)
                    ? s[2..]
                    : s;

                if (!uint.TryParse(clean, System.Globalization.NumberStyles.HexNumber,
                                   null, out var value))
                {
                    return BadRequest($"Instructiune invalida: {s}");
                }

                parsed.Add(value);
            }

            _instructionQueue.Enqueue(userId, parsed);

            return Ok();
        }


    }
}
