#!/usr/bin/python3.5

# README
# GPL

##########################################################################
# DEPENDENCIES
##########################################################################

# xmldict: python3-xmltodict under Debian/Ubuntu
import xmltodict

# Python native
from collections import OrderedDict
import re


##########################################################################
# FUNCTIONS
##########################################################################

#_________________________________________________________________________
# Customise the Master node
def buildMasterNode(Master, config):
	# Modify Info -> Source
	# How?

	return Master


#_________________________________________________________________________
# Customise the Cyclic node
def buildCyclicNode(Cyclic, config):
	# Cyclic node shorthand
	c = Cyclic['Cyclic']
	
	# Get number of boards and datalength per board
	N		= int(config['slaves']['N'])
	DataLength	= int(config['slaves']['DataLength_per_board'])
	
	# Modify both <Cmd> entries
	for i in range(0, len(c['Frame']['Cmd'])):
		# Get node
		Cmd = c['Frame']['Cmd'][i]
		
		# Change the child nodes depending on the value of Cmd
		if Cmd['Cmd'] == 12:
			Cmd['DataLength']	= 3 * DataLength
			Cmd['Cnt']		= 3 * N
		elif Cmd['Cmd'] == 9:
			Cmd['Cnt']		= N
			Cmd['InputOffs']	= DataLength + N * DataLength
			Cmd['OutputOffs']	= DataLength + N * DataLength
			
	# Set Cyclic node back into Cyclic object (required for added fields)
	Cyclic['Cyclic'] = c

	return Cyclic


#_________________________________________________________________________
# Customise the ProcessImage node
def buildProcessImageNode(ProcessImage, config):
	# Main node shorthand
	p = ProcessImage['ProcessImage']
	
	# Add empty Variable lists to Inputs and Outputs
	p['Inputs']	= OrderedDict(p['Inputs'], **{'Variable': []})
	p['Outputs']	= OrderedDict(p['Outputs'], **{'Variable': []})
	
	for i in range(0, config['slaves']['N']):
		# Get Receive and Transmit PDO templates for this slave
		if config['slaves']['types'][i] == "Slave_phil_boards":
			f = open('templates/ProcessImage_Outputs_Receive_PDO_phil_boards.xml')
			Receive_PDO = xmltodict.parse(f.read())
			f.close()
			f = open('templates/ProcessImage_Inputs_Transmit_PDO_phil_boards.xml')
			Transmit_PDO = xmltodict.parse(f.read())
			f.close()
			
		elif config['slaves']['types'][i] == "Slave_centauro_med":
			print("Centauro boards not fully supported yet. Aborting.")
			quit()
			
		# Modify the Transmit_PDO variables
		for var in Transmit_PDO['Inputs']['Variable']:
			# Regular expression replace on the name
			var['Name'] = re.sub('^Box\.', 'Box ' + str(i+1) + '.', var['Name'])
			
			# Calculate correct byte offset
			# Each board's first field has offset 208 + i*224 (where i=0,1,...)
			# i.e. each field should be offset by i*224
			var['BitOffs'] = int(var['BitOffs']) + i * 224

		# Add Transmit PDO to Inputs
		p['Inputs']['Variable'] = p['Inputs']['Variable'] + Transmit_PDO['Inputs']['Variable']
		
		# Modify the Receive_PDO variables
		for var in Receive_PDO['Outputs']['Variable']:
			# Regular expression replace on the name
			var['Name'] = re.sub('^Box\.', 'Box ' + str(i+1) + '.', var['Name'])
			
			# Calculate correct byte offset
			# Each board's first field has offset 208 + i*224 (where i=0,1,...)
			# i.e. each field should be offset by i*224
			var['BitOffs'] = int(var['BitOffs']) + i * 224
		
		# Add Receive PDO to Outputs
		p['Outputs']['Variable'] = p['Outputs']['Variable'] + Receive_PDO['Outputs']['Variable']
		
	# Add the static variables to the Output variables
	f = open('templates/ProcessImage_Outputs_static_variables.xml')
	Outputs_static_variables = xmltodict.parse(f.read())
	f.close()
	p['Outputs']['Variable'] = p['Outputs']['Variable'] + Outputs_static_variables['Outputs']['Variable']
	
	# Set main ProcessImage node back into ProcessImage object (required for added fields)
	ProcessImage['ProcessImage'] = p
	
	return ProcessImage


#_________________________________________________________________________
# Customise Slave nodes
def buildSlaveNode(Slave, i, config):
	# Main Slave node shorthand
	s = Slave['Slave']
	
	# Get datalength per board
	DataLength = int(config['slaves']['DataLength_per_board'])
	
	# Calculate things we need multiple times
	PhysAddr	= int(s['Info']['PhysAddr']) + i
	# AutoIncAddr/Adp
	Adp		= (65536 - i) % 65536

	# Modify Info node
	s['Info']['Name']		= 'Box ' + str(i+1)
	s['Info']['PhysAddr']		= PhysAddr
	s['Info']['AutoIncAddr']	= Adp
	
	# Modify ProcessData node
	s['ProcessData']['Send']['BitStart'] = int(s['ProcessData']['Send']['BitStart']) + i * int(s['ProcessData']['Send']['BitLength'])
	s['ProcessData']['Recv']['BitStart'] = int(s['ProcessData']['Recv']['BitStart']) + i * int(s['ProcessData']['Recv']['BitLength'])

	# Modify InitCmds
	# We have different changes depending on the <Cmd> node value of the InitCmd
	for j in range(0, len(s['InitCmds']['InitCmd'])):
		# Get node
		InitCmd = s['InitCmds']['InitCmd'][j]
		
		# Replace Adp node for Cmd 1, 2, 4 and 5
		if int(InitCmd['Cmd']) == 1 or int(InitCmd['Cmd']) == 2:
			InitCmd['Adp'] = Adp
		elif int(InitCmd['Cmd']) == 4 or int(InitCmd['Cmd']) == 5:
			InitCmd['Adp'] = PhysAddr
			
		# Modify Data node (counting field in hex)
		# e903, ea03, eb03, ... is 233+i in hex
		if InitCmd['Data'] == "e903":
			InitCmd['Data'] = hex(233+i)[2:] + "03"
		
		# Modify Data node
		# 000000011c0000070012000201000000,
		# 1c0000011c0000070012000201000000,
		# 380000011c0000070016000101000000
		# First 2 chars are i * DataLength in hex
		# We do this for two fields which follow the same pattern
		if InitCmd['Data'] == "000000011c0000070012000201000000" or InitCmd['Data'] == "000000011c0000070016000101000000":
			new = hex(i * DataLength)[2:]
			#print("Found, replacing first chars by " + new)
			InitCmd['Data'] = new + InitCmd['Data'][len(new):]
			#print("Result is " + InitCmd['Data'])
			
		# Place back modified InitCmd node (required for added fields)
		s['InitCmds']['InitCmd'][j] = InitCmd
		
	
	# Add a PreviousPort node if this is not the first Slave
	if i > 0:
		# Get PreviousPort template
		f = open('templates/PreviousPort.xml')
		PreviousPort = xmltodict.parse(f.read())
		f.close()
		
		# Modify appropriately
		# It refers to the previous board, i.e. address - 1
		PreviousPort['PreviousPort']['PhysAddr'] = PhysAddr - 1
		
		# Append to slave
		s = OrderedDict(s, **PreviousPort)
	
	# Set main slave node back into Slave object (required for added fields)
	Slave['Slave'] = s

	return Slave


##########################################################################
# MAIN
##########################################################################

#_________________________________________________________________________
# Main function
def main():
	#_________________________________________________________________________
	# Configuration of the to be generated EtherCAT Network Information (ENI)
	# (*.xml) file

	config = {	
		'slaves':	{	'N': 2,
					'types': [	'Slave_phil_boards',
							'Slave_phil_boards',
							'Slave_phil_boards'	],
					'DataLength_per_board': 28
				}
	}


	#_________________________________________________________________________
	# Generate main <EtherCATConfig> and <Config> nodes

	# Generate eni dict from EtherCATConfig.xml
	f = open('templates/EtherCATConfig.xml')
	ENI = xmltodict.parse(f.read())
	f.close()


	#_________________________________________________________________________
	# Add <Master> node

	f = open('templates/Master.xml')
	Master = xmltodict.parse(f.read())
	f.close()

	# Customise node
	Master = buildMasterNode(Master, config)

	# Add as child of Config
	ENI['EtherCATConfig']['Config'] = Master


	#_________________________________________________________________________
	# Add <Slave> nodes

	# Build list of Slave nodes
	Slaves = []
	for i in range(0, config['slaves']['N']):
		# Get slave template and add to Slaves
		f = open('templates/' + config['slaves']['types'][i] + '.xml')
		Slave = xmltodict.parse(f.read())
		f.close()

		# Customise node
		Slave = buildSlaveNode(Slave, i, config)

		# Append slave node
		Slaves.append(Slave['Slave'])

	# Merge OrderedDicts
	# See https://stackoverflow.com/questions/38987/how-to-merge-two-python-dictionaries-in-a-single-expression
	ENI['EtherCATConfig']['Config'] = OrderedDict(ENI['EtherCATConfig']['Config'], **{'Slave': Slaves})


	#_________________________________________________________________________
	# Add <Cyclic> node

	f = open('templates/Cyclic.xml')
	Cyclic = xmltodict.parse(f.read())
	f.close()

	# Customise node
	Cyclic = buildCyclicNode(Cyclic, config)

	# Add as child of Config
	ENI['EtherCATConfig']['Config'] = OrderedDict(ENI['EtherCATConfig']['Config'], **Cyclic)


	#_________________________________________________________________________
	# Add <ProcessImage> node

	f = open('templates/ProcessImage.xml')
	ProcessImage = xmltodict.parse(f.read())
	f.close()

	# Customise node
	ProcessImage = buildProcessImageNode(ProcessImage, config)

	# Add as child of Config
	ENI['EtherCATConfig']['Config'] = OrderedDict(ENI['EtherCATConfig']['Config'], **ProcessImage)


	#_________________________________________________________________________
	# Output

	print("Writing result to ENI.xml..")
	fout = open("ENI.xml", 'w')
	fout.write(xmltodict.unparse(ENI, pretty=True))
	fout.close()


#_________________________________________________________________________
# Execute only if run as a script
if __name__ == "__main__":
    main()


