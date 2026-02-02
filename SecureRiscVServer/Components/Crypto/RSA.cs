using System.Numerics;
using System.Security.Cryptography;
using System.Text;
using System.Collections.Generic;

namespace SecureRiscVServer.Components.Crypto
{
    public class RSA
    {
        public (BigInteger e, BigInteger n) PublicKey { get; private set; }
        private (BigInteger d, BigInteger n) PrivateKey;

        public void GenerateKeys(int keySize = 1024)
        {
            BigInteger p, q;
            do
            {
                p = GeneratePrime(keySize / 2);
                q = GeneratePrime(keySize / 2);
            } while (p == q);

            BigInteger n = p * q;
            BigInteger phi = (p - 1) * (q - 1);

            BigInteger e = 65537;
            BigInteger d = ModInverse(e, phi);

            PublicKey = (e, n);
            PrivateKey = (d, n);
        }

        public byte[] Decrypt(BigInteger cipher)
        {
            BigInteger m = BigInteger.ModPow(cipher, PrivateKey.d, PrivateKey.n);

            // Obținem exact 48 bytes în big-endian, unsigned
            byte[] bytes = m.ToByteArray(isUnsigned: true, isBigEndian: true);

            if (bytes.Length < 48)
            {
                // Prepend cu zerouri dacă e nevoie
                byte[] padded = new byte[48];
                Buffer.BlockCopy(bytes, 0, padded, 48 - bytes.Length, bytes.Length);
                bytes = padded;
            }

            return bytes;
        }


        public BigInteger DecryptInteger(BigInteger cipher)
        {
            return BigInteger.ModPow(cipher, PrivateKey.d, PrivateKey.n);
        }
        private static BigInteger ModInverse(BigInteger a, BigInteger m)
        {
            var (g, x, _) = ExtendedGcd(a, m);
            return (x % m + m) % m;
        }

        private static (BigInteger, BigInteger, BigInteger) ExtendedGcd(BigInteger a, BigInteger b)
        {
            if (a == 0) return (b, 0, 1);
            var (g, x1, y1) = ExtendedGcd(b % a, a);
            return (g, y1 - (b / a) * x1, x1);
        }

        private static BigInteger GeneratePrime(int bits)
        {
            BigInteger p;
            do
            {
                p = RandomBigInteger(bits);
            } while (!IsProbablyPrime(p));
            return p;
        }

        private static BigInteger RandomBigInteger(int bits)
        {
            byte[] bytes = new byte[bits / 8];
            RandomNumberGenerator.Fill(bytes);
            bytes[^1] &= 0x7F;
            return new BigInteger(bytes);
        }

        private static bool IsProbablyPrime(BigInteger n, int k = 10)
        {
            if (n < 2) return false;
            if (n == 2 || n == 3) return true;
            if (n % 2 == 0) return false;

            // scriem n − 1 = d * 2^s
            BigInteger d = n - 1;
            int s = 0;
            while (d % 2 == 0)
            {
                d /= 2;
                s++;
            }

            byte[] bytes = new byte[n.ToByteArray().Length];

            for (int i = 0; i < k; i++)
            {
                BigInteger a;
                do
                {
                    RandomNumberGenerator.Fill(bytes);
                    a = new BigInteger(bytes);
                }
                while (a < 2 || a >= n - 2);

                BigInteger x = BigInteger.ModPow(a, d, n);
                if (x == 1 || x == n - 1)
                    continue;

                bool composite = true;
                for (int r = 0; r < s - 1; r++)
                {
                    x = BigInteger.ModPow(x, 2, n);
                    if (x == n - 1)
                    {
                        composite = false;
                        break;
                    }
                }

                if (composite)
                    return false;
            }

            return true;
        }

    }

}
