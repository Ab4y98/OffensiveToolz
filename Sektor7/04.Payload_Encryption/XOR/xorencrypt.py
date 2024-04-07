# Red Team Operator course code template
# payload encryption with XOR
#
# author: reenz0h (twitter: @sektor7net)

import sys

KEY = "1a92038174f00df5d2869f6a63f2bdca070629ebb248c4c95f15322d164725fe"

def xor(data, key):
	
	key = str(key)
	l = len(key)
	output_str = ""

	for i in range(len(data)):
		current = data[i]
		current_key = key[i % len(key)]
		output_str += chr(ord(current) ^ ord(current_key))
	
	return output_str

def printCiphertext(ciphertext):
	print('{ 0x' + ', 0x'.join(hex(ord(x))[2:] for x in ciphertext) + ' };')



try:
    plaintext = open(sys.argv[1], "rb").read()
except:
    print("File argument needed! %s <raw payload file>" % sys.argv[0])
    sys.exit()


ciphertext = xor(plaintext, KEY)
print('{ 0x' + ', 0x'.join(hex(ord(x))[2:] for x in ciphertext) + ' };')
